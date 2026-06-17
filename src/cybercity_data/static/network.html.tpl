<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CyberCity — Network Graph</title>
  <script>{{D3_JS}}</script>
  <style>
    :root {
      --bg: #0f1117;
      --panel: #161922;
      --panel-border: #2a2f3d;
      --text: #e0e2e8;
      --muted: #8b92a8;
      --accent: #5c7cfa;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      overflow: hidden;
    }
    #app {
      display: grid;
      grid-template-columns: 1fr 320px;
      grid-template-rows: auto 1fr;
      height: 100vh;
    }
    header {
      grid-column: 1 / -1;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
      padding: 0.75rem 1.25rem;
      background: var(--panel);
      border-bottom: 1px solid var(--panel-border);
    }
    header h1 {
      margin: 0;
      font-size: 1.1rem;
      font-weight: 600;
    }
    header .meta {
      display: flex;
      gap: 1.25rem;
      color: var(--muted);
      font-size: 0.85rem;
    }
    #graph {
      position: relative;
      overflow: hidden;
    }
    #graph svg {
      width: 100%;
      height: 100%;
      cursor: grab;
    }
    #graph svg:active { cursor: grabbing; }
    aside {
      background: var(--panel);
      border-left: 1px solid var(--panel-border);
      padding: 1rem;
      overflow-y: auto;
    }
    aside h2 {
      margin: 0 0 0.75rem;
      font-size: 0.9rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--muted);
    }
    .legend {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      margin-bottom: 1.25rem;
    }
    .legend-item {
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      font-size: 0.75rem;
      padding: 0.2rem 0.5rem;
      background: rgba(255,255,255,0.05);
      border-radius: 0.25rem;
      cursor: pointer;
      user-select: none;
      transition: background 0.15s;
    }
    .legend-item:hover { background: rgba(255,255,255,0.1); }
    .legend-item.dimmed { opacity: 0.35; }
    .legend-dot {
      width: 0.6rem;
      height: 0.6rem;
      border-radius: 50%;
    }
    .card {
      background: rgba(255,255,255,0.03);
      border: 1px solid var(--panel-border);
      border-radius: 0.5rem;
      padding: 0.75rem;
      margin-bottom: 0.75rem;
    }
    .card h3 {
      margin: 0 0 0.5rem;
      font-size: 1rem;
      font-weight: 600;
    }
    .card p { margin: 0.25rem 0; font-size: 0.8rem; color: var(--muted); }
    .card .value { color: var(--text); }
    .badge {
      display: inline-block;
      font-size: 0.7rem;
      padding: 0.15rem 0.4rem;
      border-radius: 0.25rem;
      background: rgba(92,124,250,0.15);
      color: var(--accent);
      margin-right: 0.35rem;
      margin-bottom: 0.35rem;
    }
    .controls {
      display: flex;
      gap: 0.5rem;
      margin-bottom: 1rem;
    }
    .controls button {
      background: rgba(255,255,255,0.06);
      border: 1px solid var(--panel-border);
      color: var(--text);
      border-radius: 0.35rem;
      padding: 0.4rem 0.7rem;
      font-size: 0.8rem;
      cursor: pointer;
    }
    .controls button:hover { background: rgba(255,255,255,0.12); }
    .empty-state {
      color: var(--muted);
      font-size: 0.85rem;
      line-height: 1.5;
    }
    .link {
      fill: none;
      stroke: #5c6a85;
      stroke-opacity: 0.5;
      stroke-width: 1.5px;
      transition: stroke-opacity 0.2s, stroke 0.2s, stroke-width 0.2s;
      cursor: pointer;
    }
    .link:hover { stroke: var(--accent); stroke-opacity: 0.9; stroke-width: 2.5px; }
    .link.highlight { stroke: var(--accent); stroke-opacity: 0.9; stroke-width: 2.5px; }
    .link.dimmed { stroke-opacity: 0.06; }
    .link-label {
      fill: var(--muted);
      font-size: 9px;
      pointer-events: none;
      text-anchor: middle;
      paint-order: stroke;
      stroke: var(--bg);
      stroke-width: 3px;
      stroke-linecap: round;
      stroke-linejoin: round;
    }
    .link-label.dimmed { opacity: 0.06; }
    .link-label-bg {
      fill: var(--bg);
      opacity: 0.85;
      pointer-events: none;
    }
    .node {
      cursor: pointer;
      transition: filter 0.15s;
    }
    .node circle.core {
      stroke: var(--bg);
      stroke-width: 2px;
    }
    .node circle.halo {
      fill: none;
      stroke-width: 3px;
      opacity: 0.65;
    }
    .node.dimmed { opacity: 0.15; }
    .node.highlight .core { filter: drop-shadow(0 0 6px var(--accent)); }
    .node.search-match .core { filter: drop-shadow(0 0 8px #fcc419); }
    .node-label {
      fill: var(--text);
      font-size: 10px;
      pointer-events: none;
      text-anchor: middle;
      text-shadow: 0 1px 3px var(--bg);
      paint-order: stroke;
      stroke: var(--bg);
      stroke-width: 3px;
      stroke-linecap: round;
      stroke-linejoin: round;
    }
    .node-label.dimmed { opacity: 0.1; }
    .tooltip {
      position: absolute;
      background: rgba(22,25,34,0.95);
      border: 1px solid var(--panel-border);
      border-radius: 0.35rem;
      padding: 0.5rem 0.75rem;
      font-size: 0.75rem;
      color: var(--text);
      pointer-events: none;
      opacity: 0;
      transition: opacity 0.15s;
      max-width: 260px;
      z-index: 10;
    }
    .search {
      background: rgba(255,255,255,0.05);
      border: 1px solid var(--panel-border);
      border-radius: 0.35rem;
      color: var(--text);
      padding: 0.4rem 0.6rem;
      font-size: 0.85rem;
      width: 220px;
    }
    .search::placeholder { color: var(--muted); }
  </style>
</head>
<body>
  <div id="app">
    <header>
      <h1>🌆 CyberCity Network Graph</h1>
      <input id="search" class="search" type="text" placeholder="Найти сервис или организацию…">
      <div class="meta">
        <span id="meta-orgs">orgs: —</span>
        <span id="meta-services">services: —</span>
        <span id="meta-links">links: —</span>
      </div>
    </header>
    <div id="graph">
      <svg id="svg"></svg>
      <div id="tooltip" class="tooltip"></div>
    </div>
    <aside>
      <h2>Фильтры по типу сервиса</h2>
      <div id="legend" class="legend"></div>

      <h2>Фильтры по организации</h2>
      <div id="org-legend" class="legend"></div>

      <h2>Критичность</h2>
      <div id="criticality-legend" class="legend"></div>

      <div class="controls">
        <button id="reset-zoom">Сбросить зум</button>
        <button id="pause">Пауза симуляции</button>
        <button id="reset-filters">Сбросить фильтры</button>
      </div>

      <h2>Выбранный сервис / связь</h2>
      <div id="details" class="empty-state">
        Кликните по узлу или ребру, чтобы увидеть детали.
      </div>
    </aside>
  </div>

  <script>
    const TOPOLOGY = {{TOPOLOGY_JSON}};

    const KINDS = {
      web:          { color: '#5c7cfa', label: 'web' },
      api:          { color: '#20c997', label: 'api' },
      db:           { color: '#e8590c', label: 'db' },
      identity:     { color: '#fcc419', label: 'identity' },
      dns:          { color: '#66a80f', label: 'dns' },
      ntp:          { color: '#82c91e', label: 'ntp' },
      log:          { color: '#9775fa', label: 'log' },
      mail:         { color: '#f783ac', label: 'mail' },
      'file-share': { color: '#3bc9db', label: 'file-share' },
      pos:          { color: '#ff922b', label: 'pos' },
      ot:           { color: '#ff6b6b', label: 'ot' },
      iot:          { color: '#868e96', label: 'iot' },
    };
    const DEFAULT_KIND_COLOR = '#adb5bd';
    const CRITICALITY = {
      critical: { color: '#fa5252', label: 'critical' },
      high:     { color: '#fd7e14', label: 'high' },
      medium:   { color: '#fcc419', label: 'medium' },
      low:      { color: '#51cf66', label: 'low' },
    };
    const ORG_COLORS = d3.schemeTableau10;

    function main() {
      const data = TOPOLOGY;
      const nodes = data.nodes.map(n => ({ ...n }));
      const links = data.edges.map(e => ({ source: e.from, target: e.to, ...e }));
      const orgs = Array.from(new Set(nodes.map(n => n.org_id))).sort();
      const orgColor = d3.scaleOrdinal(ORG_COLORS).domain(orgs);

      document.getElementById('meta-orgs').textContent = `orgs: ${data.summary.organizations}`;
      document.getElementById('meta-services').textContent = `services: ${data.summary.services}`;
      document.getElementById('meta-links').textContent = `links: ${data.summary.links}`;

      const kinds = Array.from(new Set(nodes.map(n => n.kind))).sort();
      const activeKinds = new Set(kinds);

      const activeOrgs = new Set(orgs);

      const legendEl = document.getElementById('legend');
      kinds.forEach(kind => {
        const item = document.createElement('span');
        item.className = 'legend-item';
        item.dataset.kind = kind;
        const dot = document.createElement('span');
        dot.className = 'legend-dot';
        dot.style.background = (KINDS[kind] || {}).color || DEFAULT_KIND_COLOR;
        const label = document.createElement('span');
        label.textContent = kind;
        item.append(dot, label);
        item.addEventListener('click', () => {
          if (activeKinds.has(kind)) {
            if (activeKinds.size > 1) activeKinds.delete(kind);
          } else {
            activeKinds.add(kind);
          }
          item.classList.toggle('dimmed', !activeKinds.has(kind));
          updateVisibility();
        });
        legendEl.appendChild(item);
      });

      const orgLegendEl = document.getElementById('org-legend');
      orgs.forEach((org, idx) => {
        const item = document.createElement('span');
        item.className = 'legend-item';
        item.dataset.org = org;
        const dot = document.createElement('span');
        dot.className = 'legend-dot';
        dot.style.background = ORG_COLORS[idx % ORG_COLORS.length];
        const label = document.createElement('span');
        label.textContent = org;
        item.append(dot, label);
        item.addEventListener('click', () => {
          if (activeOrgs.has(org)) {
            if (activeOrgs.size > 1) activeOrgs.delete(org);
          } else {
            activeOrgs.add(org);
          }
          item.classList.toggle('dimmed', !activeOrgs.has(org));
          updateVisibility();
        });
        orgLegendEl.appendChild(item);
      });

      const criticalityLegendEl = document.getElementById('criticality-legend');
      Object.entries(CRITICALITY).forEach(([level, cfg]) => {
        const item = document.createElement('span');
        item.className = 'legend-item';
        const dot = document.createElement('span');
        dot.className = 'legend-dot';
        dot.style.background = cfg.color;
        const label = document.createElement('span');
        label.textContent = cfg.label;
        item.append(dot, label);
        criticalityLegendEl.appendChild(item);
      });

      const container = document.getElementById('graph');
      const svg = d3.select('#svg');
      const width = container.clientWidth;
      const height = container.clientHeight;

      const g = svg.append('g');
      const zoom = d3.zoom()
        .scaleExtent([0.05, 6])
        .on('zoom', (e) => g.attr('transform', e.transform));
      svg.call(zoom);

      // Marker for directed edges.
      svg.append('defs').selectAll('marker')
        .data(['arrow'])
        .join('marker')
        .attr('id', d => d)
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 22)
        .attr('refY', 0)
        .attr('markerWidth', 6)
        .attr('markerHeight', 6)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M0,-5L10,0L0,5')
        .attr('fill', '#5c6a85');

      const simulation = d3.forceSimulation(nodes)
        .force('link', d3.forceLink(links).id(d => d.id).distance(240))
        .force('charge', d3.forceManyBody().strength(-1000))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collide', d3.forceCollide().radius(48));

      // Compute offsets for multiple links between the same pair of nodes.
      const linkKey = (a, b) => [a, b].sort().join('||');
      const linkGroups = {};
      links.forEach(l => {
        const key = linkKey(l.source.id || l.source, l.target.id || l.target);
        (linkGroups[key] = linkGroups[key] || []).push(l);
      });
      const linkIndexInGroup = new Map();
      Object.values(linkGroups).forEach(group => {
        const total = group.length;
        group.forEach((l, i) => {
          linkIndexInGroup.set(l, { index: i, total });
        });
      });

      const linkG = g.append('g').attr('class', 'links');
      const link = linkG.selectAll('path.link')
        .data(links)
        .join('path')
        .attr('class', 'link')
        .attr('marker-end', 'url(#arrow)')
        .on('mouseenter', (e, d) => {
          tooltip.style.opacity = 1;
          tooltip.innerHTML = `<strong>${d.source.id} → ${d.target.id}</strong><br>${d.kind}${d.protocol ? ' @ ' + d.protocol : ''}${d.encryption ? ' (' + d.encryption + ')' : ''}`;
        })
        .on('mousemove', (e) => {
          tooltip.style.left = (e.pageX + 12) + 'px';
          tooltip.style.top = (e.pageY + 12) + 'px';
        })
        .on('mouseleave', () => { tooltip.style.opacity = 0; })
        .on('click', (e, d) => { e.stopPropagation(); showLinkDetails(d); });

      const linkLabelBg = linkG.selectAll('rect.link-label-bg')
        .data(links)
        .join('rect')
        .attr('class', 'link-label-bg')
        .attr('rx', 3)
        .attr('ry', 3);

      const linkLabel = linkG.selectAll('text.link-label')
        .data(links)
        .join('text')
        .attr('class', 'link-label')
        .text(d => d.kind);

      const node = g.append('g')
        .attr('class', 'nodes')
        .selectAll('g')
        .data(nodes)
        .join('g')
        .attr('class', 'node')
        .call(d3.drag()
          .on('start', (e, d) => {
            if (!e.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x; d.fy = d.y;
          })
          .on('drag', (e, d) => { d.fx = e.x; d.fy = e.y; })
          .on('end', (e, d) => {
            if (!e.active) simulation.alphaTarget(0);
            d.fx = null; d.fy = null;
          }));

      node.append('circle')
        .attr('class', 'halo')
        .attr('r', d => d.is_honeypot ? 13 : 17)
        .attr('stroke', d => (CRITICALITY[d.criticality] || {}).color || '#adb5bd');

      node.append('circle')
        .attr('class', 'core')
        .attr('r', d => d.is_honeypot ? 10 : 14)
        .attr('fill', d => (KINDS[d.kind] || {}).color || DEFAULT_KIND_COLOR)
        .attr('stroke', d => orgColor(d.org_id));

      const labels = g.append('g')
        .attr('class', 'labels')
        .selectAll('text')
        .data(nodes)
        .join('text')
        .attr('class', 'node-label')
        .attr('text-anchor', 'middle')
        .attr('dy', 26)
        .text(d => d.id);

      const tooltip = document.getElementById('tooltip');

      node
        .on('mouseenter', (e, d) => {
          tooltip.style.opacity = 1;
          tooltip.innerHTML = `<strong>${d.id}</strong><br>${d.org_name}<br>${d.kind} @ ${d.bind_ip || '—'}`;
        })
        .on('mousemove', (e) => {
          tooltip.style.left = (e.pageX + 12) + 'px';
          tooltip.style.top = (e.pageY + 12) + 'px';
        })
        .on('mouseleave', () => { tooltip.style.opacity = 0; })
        .on('click', (e, d) => { e.stopPropagation(); showNodeDetails(d); });

      svg.on('click', () => { clearSelection(); });

      function linkPath(d) {
        const sx = d.source.x, sy = d.source.y;
        const tx = d.target.x, ty = d.target.y;
        const group = linkIndexInGroup.get(d);
        if (!group || group.total <= 1) {
          return `M${sx},${sy}L${tx},${ty}`;
        }
        // Curved parallel edges: offset perpendicular to the chord.
        const dx = tx - sx;
        const dy = ty - sy;
        const len = Math.sqrt(dx * dx + dy * dy) || 1;
        const perpX = -dy / len;
        const perpY = dx / len;
        const offset = (group.index - (group.total - 1) / 2) * 14;
        const mx = (sx + tx) / 2 + perpX * offset;
        const my = (sy + ty) / 2 + perpY * offset;
        return `M${sx},${sy}Q${mx},${my} ${tx},${ty}`;
      }

      function shortenEnd(d, t = 0.88) {
        const sx = d.source.x, sy = d.source.y;
        const tx = d.target.x, ty = d.target.y;
        const group = linkIndexInGroup.get(d);
        if (!group || group.total <= 1) {
          const x = sx + (tx - sx) * t;
          const y = sy + (ty - sy) * t;
          return { x, y };
        }
        const pathEl = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        pathEl.setAttribute('d', linkPath(d));
        const total = pathEl.getTotalLength();
        return pathEl.getPointAtLength(total * t);
      }

      simulation.on('tick', () => {
        link.attr('d', d => linkPath(d));
        // Move arrowhead to ~88% along the path so it doesn't sit under the target circle.
        link.each(function(d) {
          const end = shortenEnd(d, 0.88);
          const near = shortenEnd(d, 0.87);
          const angle = Math.atan2(end.y - near.y, end.x - near.x) * 180 / Math.PI;
          d3.select(this).attr('marker-end', `url(#arrow)`)
            .style('marker-end-transform', `rotate(${angle}deg)`);
        });

        linkLabel
          .attr('x', d => {
            const group = linkIndexInGroup.get(d);
            if (!group || group.total <= 1) return (d.source.x + d.target.x) / 2;
            const mid = (d.source.x + d.target.x) / 2;
            const dx = d.target.x - d.source.x;
            const dy = d.target.y - d.source.y;
            const len = Math.sqrt(dx * dx + dy * dy) || 1;
            const perpX = -dy / len;
            const offset = (group.index - (group.total - 1) / 2) * 14;
            return mid + perpX * offset;
          })
          .attr('y', d => {
            const group = linkIndexInGroup.get(d);
            if (!group || group.total <= 1) return (d.source.y + d.target.y) / 2;
            const mid = (d.source.y + d.target.y) / 2;
            const dx = d.target.x - d.source.x;
            const dy = d.target.y - d.source.y;
            const len = Math.sqrt(dx * dx + dy * dy) || 1;
            const perpY = dx / len;
            const offset = (group.index - (group.total - 1) / 2) * 14;
            return mid + perpY * offset;
          });

        linkLabelBg.each(function(d) {
          const textNode = linkLabel.nodes()[links.indexOf(d)];
          const bbox = textNode.getBBox();
          d3.select(this)
            .attr('x', bbox.x - 2)
            .attr('y', bbox.y - 1)
            .attr('width', bbox.width + 4)
            .attr('height', bbox.height + 2);
        });

        node.attr('transform', d => `translate(${d.x},${d.y})`);
        labels.attr('x', d => d.x).attr('y', d => d.y);
      });

      let selectedId = null;
      let selectedLink = null;
      let searchMatchId = null;

      function showNodeDetails(d) {
        selectedId = d.id;
        selectedLink = null;
        const outgoing = links.filter(l => l.source.id === d.id);
        const incoming = links.filter(l => l.target.id === d.id);
        const ports = (d.ports || []).map(p => `<span class="badge">${p}</span>`).join('');
        const kindColor = (KINDS[d.kind] || {}).color || DEFAULT_KIND_COLOR;

        document.getElementById('details').innerHTML = `
          <div class="card">
            <h3 style="color:${kindColor}">${d.id}</h3>
            <p><span class="value">${d.name || d.id}</span></p>
            <p>${d.description || ''}</p>
            <p><strong>Организация:</strong> <span class="value">${d.org_name} (${d.org_id})</span></p>
            <p><strong>Сеть:</strong> <span class="value">${d.network_id || '—'}</span></p>
            <p><strong>IP:</strong> <span class="value">${d.bind_ip || '—'}</span></p>
            <p><strong>Хост:</strong> <span class="value">${d.host || '—'}</span></p>
            <p><strong>Тип:</strong> <span class="value">${d.kind}</span></p>
            <p><strong>Exposure:</strong> <span class="value">${d.exposure}</span></p>
            <p><strong>Критичность:</strong> <span class="value">${d.criticality}</span></p>
            <p><strong>Auth:</strong> <span class="value">${d.auth}</span></p>
            <p><strong>Данные:</strong> <span class="value">${d.data_classification}</span></p>
            ${ports ? `<p><strong>Порты:</strong> ${ports}</p>` : ''}
            ${d.is_honeypot ? '<p><span class="badge" style="background:rgba(255,107,107,0.2);color:#ff6b6b">honeypot</span></p>' : ''}
          </div>
          ${renderConnections('Исходящие связи', outgoing, 'target')}
          ${renderConnections('Входящие связи', incoming, 'source')}
        `;

        updateHighlight();
      }

      function showLinkDetails(d) {
        selectedLink = d;
        selectedId = null;
        document.getElementById('details').innerHTML = `
          <div class="card">
            <h3>Связь</h3>
            <p><span class="value">${d.source.id}</span> → <span class="value">${d.target.id}</span></p>
            <p><strong>Тип:</strong> <span class="value">${d.kind}</span></p>
            <p><strong>Протокол:</strong> <span class="value">${d.protocol || '—'}</span></p>
            <p><strong>Шифрование:</strong> <span class="value">${d.encryption || '—'}</span></p>
            ${d.label ? `<p><strong>Описание:</strong> <span class="value">${d.label}</span></p>` : ''}
          </div>
        `;
        updateHighlight();
      }

      function renderConnections(title, list, endpoint) {
        if (!list.length) return '';
        return `
          <div class="card">
            <h3>${title}</h3>
            ${list.map(l => `
              <p>
                <span class="value">${l[endpoint].id}</span>
                <span class="badge">${l.kind}</span>
                ${l.protocol ? `<span class="badge">${l.protocol}</span>` : ''}
                ${l.encryption ? `<span class="badge">${l.encryption}</span>` : ''}
                ${l.label ? `<br><span style="color:var(--muted)">${l.label}</span>` : ''}
              </p>
            `).join('')}
          </div>
        `;
      }

      function isConnected(a, b) {
        return links.some(l =>
          (l.source.id === a && l.target.id === b) ||
          (l.source.id === b && l.target.id === a)
        );
      }

      function clearSelection() {
        selectedId = null;
        selectedLink = null;
        searchMatchId = null;
        document.getElementById('details').innerHTML =
          'Кликните по узлу или ребру, чтобы увидеть детали.';
        updateHighlight();
      }

      function isVisibleNode(d) {
        return activeKinds.has(d.kind) && activeOrgs.has(d.org_id);
      }

      function updateHighlight() {
        const isNodeSelected = selectedId !== null;
        const isLinkSelected = selectedLink !== null;

        node.classed('dimmed', d => {
          if (!isVisibleNode(d)) return true;
          if (isNodeSelected) return d.id !== selectedId && !isConnected(selectedId, d.id);
          if (isLinkSelected) return d.id !== selectedLink.source.id && d.id !== selectedLink.target.id;
          return false;
        });
        node.classed('highlight', d => {
          if (isNodeSelected) return d.id === selectedId;
          if (isLinkSelected) return d.id === selectedLink.source.id || d.id === selectedLink.target.id;
          return false;
        });
        node.classed('search-match', d => searchMatchId !== null && d.id === searchMatchId);

        link.classed('dimmed', l => {
          if (!isVisibleNode(l.source) || !isVisibleNode(l.target)) return true;
          if (isNodeSelected) return l.source.id !== selectedId && l.target.id !== selectedId;
          if (isLinkSelected) return l !== selectedLink;
          return false;
        });
        link.classed('highlight', l => {
          if (isNodeSelected) return l.source.id === selectedId || l.target.id === selectedId;
          if (isLinkSelected) return l === selectedLink;
          return false;
        });

        linkLabel.classed('dimmed', l => {
          if (!isVisibleNode(l.source) || !isVisibleNode(l.target)) return true;
          if (isNodeSelected) return l.source.id !== selectedId && l.target.id !== selectedId;
          if (isLinkSelected) return l !== selectedLink;
          return false;
        });
        linkLabelBg.classed('dimmed', l => {
          if (!isVisibleNode(l.source) || !isVisibleNode(l.target)) return true;
          if (isNodeSelected) return l.source.id !== selectedId && l.target.id !== selectedId;
          if (isLinkSelected) return l !== selectedLink;
          return false;
        });

        labels.classed('dimmed', d => {
          if (!isVisibleNode(d)) return true;
          if (isNodeSelected) return d.id !== selectedId && !isConnected(selectedId, d.id);
          if (isLinkSelected) return d.id !== selectedLink.source.id && d.id !== selectedLink.target.id;
          return false;
        });
      }

      function updateVisibility() {
        updateHighlight();
      }

      document.getElementById('reset-zoom').addEventListener('click', () => {
        svg.transition().duration(500).call(zoom.transform, d3.zoomIdentity);
      });

      document.getElementById('reset-filters').addEventListener('click', () => {
        activeKinds.clear();
        kinds.forEach(k => activeKinds.add(k));
        activeOrgs.clear();
        orgs.forEach(o => activeOrgs.add(o));
        document.querySelectorAll('.legend-item').forEach(el => el.classList.remove('dimmed'));
        document.getElementById('search').value = '';
        clearSelection();
      });

      let running = true;
      document.getElementById('pause').addEventListener('click', (e) => {
        if (running) {
          simulation.stop();
          e.target.textContent = 'Возобновить симуляцию';
        } else {
          simulation.restart();
          e.target.textContent = 'Пауза симуляции';
        }
        running = !running;
      });

      document.getElementById('search').addEventListener('input', (e) => {
        const q = e.target.value.toLowerCase();
        if (!q) { clearSelection(); return; }
        const match = nodes.find(n =>
          n.id.toLowerCase().includes(q) ||
          n.org_id.toLowerCase().includes(q) ||
          (n.org_name || '').toLowerCase().includes(q) ||
          n.host.toLowerCase().includes(q)
        );
        if (match) {
          clearSelection();
          searchMatchId = match.id;
          showNodeDetails(match);
          svg.transition().duration(500).call(
            zoom.transform,
            d3.zoomIdentity.translate(width / 2, height / 2).scale(1.2).translate(-match.x, -match.y)
          );
        }
      });
    }

    main();
  </script>
</body>
</html>
