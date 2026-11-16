// Guide page: the desktop GUI's Help -> Analysis Guide (gui_help_content.py, via /api/guide), one section at a time.
import { route, app, api, esc } from './core.js';

route('guide', async (args) => {
  const d = await api('/guide'), secs = d.sections;
  const cur = secs.find(s => s.id === args[0]) || secs[0];
  app().innerHTML = `<p class="kicker">Help → Analysis Guide</p><h1>${esc(cur.title)}</h1>
    <p class="small mute">The text of the desktop GUI's Analysis Guide (<code>gui_help_content.py</code>), shown unchanged.</p>
    <div class="side guide"><nav class="toc" aria-label="Guide sections">${secs.map(s =>
      `<a href="#/guide/${s.id}" class="${s.id === cur.id ? 'on' : ''}" ${s.id === cur.id ? 'aria-current="page"' : ''}>${esc(s.title)}</a>`).join('')}</nav>
      <pre class="guide-text">${esc(cur.body)}</pre></div>`;
});
