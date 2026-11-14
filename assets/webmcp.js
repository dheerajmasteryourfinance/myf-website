/* WebMCP: tools that in-browser AI agents can call on masteryourfinance.org.
   Registered on page load through navigator.modelContext (only in browsers/agents that support it). */
(function () {
  var mc = typeof navigator !== 'undefined' && navigator.modelContext;
  if (!mc) return;

  var CALENDLY = 'https://calendly.com/himanshu-masteryourbusiness/30-minutes-discovery-call-law-firms';
  var PAGES = ['index', 'services', 'industries', 'tools', 'about-us', 'contact-us', 'health-check', 'privacy-policy', 'terms'];
  var SERVICES = [
    { name: 'Bookkeeping & Accounting', summary: 'Clean books, reconciled accounts, and AR/AP handled every week.' },
    { name: 'Cash Flow Forecasting', summary: '13-week cash flow forecast; track DSO and chase receivables before they age.' },
    { name: 'Monthly Reporting', summary: 'Reports delivered on schedule, with the numbers explained in plain words.' },
    { name: 'CFO-Lite Support', summary: 'Guidance on hiring, pricing and growth decisions, without a full-time CFO.' },
    { name: 'Finance Operations', summary: 'Receivables and reporting run day to day.' }
  ];
  function text(t) { return { content: [{ type: 'text', text: t }] }; }
  function getText(url) { return fetch(url, { headers: { Accept: 'text/markdown, text/plain' } }).then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.text(); }); }

  var tools = [
    {
      name: 'get_site_overview',
      description: 'Summary of Master Your Finance (outsourced finance team for professional service firms in the US, UK and Australia) with links to every page.',
      inputSchema: { type: 'object', properties: {} },
      annotations: { readOnlyHint: true },
      execute: function () { return getText('/llms.txt').then(text); }
    },
    {
      name: 'list_services',
      description: 'List the finance services Master Your Finance offers, with a one-line summary of each.',
      inputSchema: { type: 'object', properties: {} },
      annotations: { readOnlyHint: true },
      execute: function () { return Promise.resolve(text(JSON.stringify(SERVICES, null, 2))); }
    },
    {
      name: 'read_page',
      description: 'Read a page of the Master Your Finance website as Markdown.',
      inputSchema: { type: 'object', properties: { page: { type: 'string', enum: PAGES, description: 'Page to read' } }, required: ['page'] },
      annotations: { readOnlyHint: true },
      execute: function (args) {
        var p = args && args.page;
        if (PAGES.indexOf(p) < 0) return Promise.resolve(text('Unknown page. Choose one of: ' + PAGES.join(', ')));
        return getText('/' + p + '.md').then(text);
      }
    },
    {
      name: 'get_booking_link',
      description: 'Get the link to book a free 30-minute finance review call with Master Your Finance.',
      inputSchema: { type: 'object', properties: {} },
      annotations: { readOnlyHint: true },
      execute: function () { return Promise.resolve(text('Book a free 30-minute finance review: ' + CALENDLY)); }
    },
    {
      name: 'send_enquiry',
      description: 'Send an enquiry to the Master Your Finance team on behalf of the user (same as the Contact Us form). Only use with the user\'s own name and work email, after they agree to send it.',
      inputSchema: {
        type: 'object',
        properties: {
          name: { type: 'string', description: 'Full name of the person enquiring' },
          email: { type: 'string', format: 'email', description: 'Their work email' },
          firm_size: { type: 'string', enum: ['11–25 staff', '26–100 staff', '101–250 staff'] },
          need: { type: 'string', enum: ['Bookkeeping & accounting', 'Cash flow forecasting', 'Monthly reporting', 'CFO-lite support', 'Finance operations', 'Not sure yet'] }
        },
        required: ['name', 'email']
      },
      annotations: { readOnlyHint: false },
      execute: function (args) {
        args = args || {};
        var body = { name: args.name || '', email: args.email || '', size: args.firm_size || '', need: args.need || '', page: location.pathname + ' (via WebMCP)' };
        return fetch('/api/contact.php', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
          .then(function (r) { return r.json().catch(function () { return {}; }).then(function (j) { return r.ok && j.ok; }); })
          .then(function (ok) { return text(ok ? 'Enquiry sent. The team will reply within one working day.' : 'The enquiry could not be sent. Please use ' + CALENDLY + ' instead.'); });
      }
    }
  ];

  try {
    if (typeof mc.registerTool === 'function') tools.forEach(function (t) { try { mc.registerTool(t); } catch (e) {} });
    else if (typeof mc.provideContext === 'function') mc.provideContext({ tools: tools });
  } catch (e) {}
})();
