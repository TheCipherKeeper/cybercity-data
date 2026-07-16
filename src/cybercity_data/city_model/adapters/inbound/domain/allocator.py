"""Automatic IP and network allocation for the CyberCity declarative model.

The allocator is the bridge between the clean declarative model (organizations,
networks by kind, services with network_id) and the concrete L3 addressing that
downstream artifacts need.

Rules:
  * Each organization receives a unique second octet (network_index) in 1..255.
  * Per-organization subnets are /24 and are chosen from kind-specific pools:
      - dmz / internet -> third octet 0..127
      - lan / ot       -> third octet 128..252
      - mgmt           -> third octet 253 (only one allowed)
  * Service bind_ip is allocated inside its network, starting at .10.

The default allocation is random (different on every build).  A fixed seed makes
it reproducible, which is useful for tests and CI.
"""

import random
import secrets
from collections.abc import Iterator

from pydantic import BaseModel, ConfigDict

from .models import CityNetwork, Network, Organization


class AllocationError(Exception):
    """Raised when the declarative model cannot be turned into a valid address plan."""


class Allocation(BaseModel):
    """Concrete addressing produced by the allocator."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    org_index: dict[str, int] = {}
    net_cidr: dict[str, str] = {}
    svc_ip: dict[str, str] = {}

    def network_index(self, org_id: str) -> int:
        return self.org_index[org_id]

    def cidr(self, net_id: str) -> str:
        return self.net_cidr[net_id]

    def bind_ip(self, svc_id: str) -> str:
        return self.svc_ip[svc_id]


class Allocator:
    """Build an :class:`Allocation` from a ``CityNetwork``.

    Args:
        network: Assembled declarative city model.
        seed: Optional random seed. If ``None`` the allocation is different every
            time; pass an integer for reproducible builds/tests.
    """

    _DMZ_KINDS = {"dmz", "internet"}
    _LAN_KINDS = {"lan", "ot"}
    _MGMT_KINDS = {"mgmt"}

    _FIRST_HOST = 10

    def __init__(self, network: CityNetwork, seed: int | None = None) -> None:
        self._network = network
        self._seed = seed if seed is not None else secrets.randbits(64)
        self._rng = random.Random(self._seed)
        self._cached_org_indices: dict[str, int] | None = None

    @property
    def seed(self) -> int:
        """The seed that was used (random or user-provided)."""
        return self._seed

    def allocate(self) -> Allocation:
        """Run the full allocation and return the result."""
        org_index = self._org_indices
        net_cidr: dict[str, str] = {}
        svc_ip: dict[str, str] = {}

        for org in self._network.organizations:
            org_nets, org_ips = self._allocate_org(org, org_index[org.id])
            net_cidr.update(org_nets)
            svc_ip.update(org_ips)

        return Allocation(org_index=org_index, net_cidr=net_cidr, svc_ip=svc_ip)

    def _allocate_org_indices(self) -> dict[str, int]:
        org_ids = [org.id for org in self._network.organizations]
        n_orgs = len(org_ids)
        if n_orgs > 255:
            raise AllocationError(
                f"too many organizations: {n_orgs}, only 255 network indices are available"
            )

        indices = list(range(1, 256))
        self._rng.shuffle(indices)
        return {org_id: indices[i] for i, org_id in enumerate(org_ids)}

    @property
    def _org_indices(self) -> dict[str, int]:
        if self._cached_org_indices is None:
            self._cached_org_indices = self._allocate_org_indices()
        return self._cached_org_indices

    def _allocate_org(
        self, org: Organization, network_index: int
    ) -> tuple[dict[str, str], dict[str, str]]:
        front_pool = iter(range(0, 128))  # dmz / internet
        back_pool = iter(range(128, 253))  # lan / ot
        mgmt_used = False

        net_cidr: dict[str, str] = {}
        for net in org.networks:
            cidr, mgmt_used = self._next_cidr(net, network_index, front_pool, back_pool, mgmt_used)
            net_cidr[net.id] = cidr

        svc_ip = self._allocate_svc_ips(org, network_index, net_cidr)
        return net_cidr, svc_ip

    def _next_cidr(
        self,
        net: Network,
        network_index: int,
        front_pool: Iterator[int],
        back_pool: Iterator[int],
        mgmt_used: bool,
    ) -> tuple[str, bool]:
        third: int
        if net.kind in self._DMZ_KINDS:
            try:
                third = next(front_pool)
            except StopIteration as exc:
                raise AllocationError(
                    f"organization {net.org_id!r}: exhausted dmz/internet subnet pool "
                    f"(kind={net.kind!r}, id={net.id!r})"
                ) from exc
        elif net.kind in self._LAN_KINDS:
            try:
                third = next(back_pool)
            except StopIteration as exc:
                raise AllocationError(
                    f"organization {net.org_id!r}: exhausted lan/ot subnet pool "
                    f"(kind={net.kind!r}, id={net.id!r})"
                ) from exc
        elif net.kind in self._MGMT_KINDS:
            if mgmt_used:
                raise AllocationError(
                    f"organization {net.org_id!r}: only one mgmt network is allowed, "
                    f"second id={net.id!r}"
                )
            third = 253
            mgmt_used = True
        else:
            raise AllocationError(
                f"organization {net.org_id!r}: unknown network kind {net.kind!r} "
                f"for network {net.id!r}"
            )

        return f"10.{network_index}.{third}.0/24", mgmt_used

    def _allocate_svc_ips(
        self, org: Organization, network_index: int, net_cidr: dict[str, str]
    ) -> dict[str, str]:
        next_host: dict[str, int] = {net_id: self._FIRST_HOST for net_id in net_cidr}
        svc_ip: dict[str, str] = {}

        for svc in self._network.services:
            if svc.org_id != org.id:
                continue
            net_id = svc.network_id
            if net_id is None:
                continue
            if net_id not in net_cidr:
                continue

            host = next_host[net_id]
            cidr = net_cidr[net_id]
            prefix = int(cidr.split("/")[1])
            total_hosts = 2 ** (32 - prefix)
            # Usable hosts: .1 .. .(total_hosts - 2). We start at _FIRST_HOST.
            if host > total_hosts - 2:
                raise AllocationError(
                    f"network {net_id!r} has no free host addresses for service {svc.id!r}"
                )

            svc_ip[svc.id] = f"10.{network_index}.{self._third_octet(cidr)}.{host}"
            next_host[net_id] = host + 1

        return svc_ip

    @staticmethod
    def _third_octet(cidr: str) -> int:
        return int(cidr.split(".")[2])
