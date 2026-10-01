/* Master Your Finance — preview runtime.
   Renders the design's .dc.html templates in a normal browser:
   {{value}} bindings, <sc-if>, <sc-for>, <dc-import>, event props and component state. */
(function () {
  'use strict';
  var SVG_NS = 'http://www.w3.org/2000/svg';
  var EVENTS = { onclick: 'click', onmouseenter: 'mouseenter', onmouseleave: 'mouseleave', onmousemove: 'mousemove',
    onfocus: 'focusin', onblur: 'focusout', onchange: 'input', onkeydown: 'keydown', onerror: 'error', onsubmit: 'submit' };
  var DIRECT = { mouseenter: 1, mouseleave: 1, error: 1 };
  var cache = {};
  var uid = 0;

  function DCLogic(props) { this.props = props || {}; this.state = {}; }
  DCLogic.prototype.setState = function (u, cb) {
    var next = typeof u === 'function' ? u(this.state, this.props) : u;
    this.state = Object.assign({}, this.state, next);
    if (this.__inst) this.__inst.schedule();
    if (cb) Promise.resolve().then(cb);
  };
  DCLogic.prototype.forceUpdate = function () { if (this.__inst) this.__inst.schedule(); };
  window.DCLogic = DCLogic;

  function load(name) {
    if (!cache[name]) {
      cache[name] = fetch(name + '.dc.html').then(function (r) { return r.text(); }).then(function (txt) {
        var doc = new DOMParser().parseFromString(txt, 'text/html');
        var xdc = doc.querySelector('x-dc');
        var helmet = xdc.querySelector('helmet');
        if (helmet) {
          Array.prototype.slice.call(helmet.children).forEach(function (n) {
            var key = n.outerHTML;
            if (!document.head.querySelector('[data-dc-helmet="' + btoa(unescape(encodeURIComponent(key))).slice(0, 40) + '"]')) {
              var c = document.importNode(n, true); c.setAttribute('data-dc-helmet', btoa(unescape(encodeURIComponent(key))).slice(0, 40)); document.head.appendChild(c);
            }
          });
          helmet.remove();
        }
        var script = doc.querySelector('script[type="text/x-dc"]');
        var defaults = {}, propKeys = {};
        try {
          var dp = JSON.parse(script.getAttribute('data-props') || '{}');
          Object.keys(dp).forEach(function (k) { if (k[0] === '$') return; propKeys[k.toLowerCase()] = k; if (dp[k] && 'default' in dp[k]) defaults[k] = dp[k]['default']; });
        } catch (e) {}
        var Comp = new Function('DCLogic', script.textContent + '\nreturn Component;')(DCLogic);
        var root = null;
        for (var i = 0; i < xdc.childNodes.length; i++) { var n = xdc.childNodes[i]; if (n.nodeType === 1) { root = n; break; } }
        return { Comp: Comp, tpl: root, defaults: defaults, propKeys: propKeys };
      });
    }
    return cache[name];
  }

  function lookup(expr, scopes) {
    expr = expr.trim();
    if (expr === 'true') return true;
    if (expr === 'false') return false;
    if (expr === 'null') return null;
    if (/^-?\d+(\.\d+)?$/.test(expr)) return parseFloat(expr);
    if (/^'.*'$|^".*"$/.test(expr)) return expr.slice(1, -1);
    var parts = expr.split('.');
    for (var i = scopes.length - 1; i >= 0; i--) {
      if (scopes[i] && parts[0] in scopes[i]) {
        var v = scopes[i][parts[0]];
        for (var j = 1; j < parts.length; j++) v = v == null ? undefined : v[parts[j]];
        return v;
      }
    }
    return undefined;
  }
  var ONE = /^\{\{([^}]*)\}\}$/;
  function interp(str, scopes) {
    return str.replace(/\{\{([^}]*)\}\}/g, function (_, e) { var v = lookup(e, scopes); return v == null || v === false ? '' : String(v); });
  }

  /* template -> virtual nodes */
  function build(node, scopes, out, inst) {
    if (node.nodeType === 3) {
      var t = node.nodeValue;
      out.push({ text: t.indexOf('{{') >= 0 ? interp(t, scopes) : t });
      return;
    }
    if (node.nodeType !== 1) return;
    var tag = node.localName;
    if (tag === 'sc-if') {
      var m = ONE.exec(node.getAttribute('value') || '');
      if (m ? lookup(m[1], scopes) : false) kids(node, scopes, out, inst);
      return;
    }
    if (tag === 'sc-for') {
      var lm = ONE.exec(node.getAttribute('list') || '');
      var list = lm ? lookup(lm[1], scopes) : null;
      var as = node.getAttribute('as') || 'item';
      (list || []).forEach(function (item, idx) { var sc = {}; sc[as] = item; sc[as + 'Index'] = idx; kids(node, scopes.concat([sc]), out, inst); });
      return;
    }
    var v = { tag: tag, attrs: {}, ev: {}, ref: null, children: [], isSvg: tag === 'svg' };
    if (tag === 'dc-import') {
      v.tag = 'div';
      v.importName = node.getAttribute('name');
      v.props = {};
      Array.prototype.forEach.call(node.attributes, function (a) {
        if (a.name === 'name' || a.name.indexOf('hint-') === 0) return;
        var mm = ONE.exec(a.value); v.props[a.name] = mm ? lookup(mm[1], scopes) : interp(a.value, scopes);
      });
      v.attrs['data-dc-host'] = v.importName;
      var hs = node.getAttribute('hint-size');
      if (hs) { var p = hs.split(','); v.attrs.style = 'width:' + p[0] + ';height:' + p[1]; }
      out.push(v);
      return;
    }
    Array.prototype.forEach.call(node.attributes, function (a) {
      var name = a.name, val = a.value;
      if (name.indexOf('hint-') === 0) return;
      if (EVENTS[name]) { var em = ONE.exec(val); if (em) { var fn = lookup(em[1], scopes); if (typeof fn === 'function') v.ev[EVENTS[name]] = fn; } return; }
      if (name === 'ref') { var rm = ONE.exec(val); if (rm) v.ref = lookup(rm[1], scopes); return; }
      if (name.indexOf('on') === 0) return; /* never emit inline handlers */
      v.attrs[name] = val.indexOf('{{') >= 0 ? interp(val, scopes) : val;
    });
    kids(node, scopes, v.children, inst);
    out.push(v);
  }
  function kids(node, scopes, out, inst) { for (var c = node.firstChild; c; c = c.nextSibling) build(c, scopes, out, inst); }

  /* virtual nodes -> DOM */
  function create(v, svg, inst) {
    if ('text' in v) return document.createTextNode(v.text);
    var isSvg = svg || v.tag === 'svg';
    var el = isSvg ? document.createElementNS(SVG_NS, v.tag) : document.createElement(v.tag);
    el.__dcNew = true;
    update(el, v, isSvg, inst);
    return el;
  }
  function setAttrs(el, v) {
    var old = el.__dcAttrs || {};
    Object.keys(old).forEach(function (k) { if (!(k in v.attrs)) el.removeAttribute(k); });
    Object.keys(v.attrs).forEach(function (k) {
      var val = v.attrs[k];
      if (old[k] !== val) {
        try { el.setAttribute(k, val); } catch (e) {}
        if (k === 'value' && 'value' in el && el.value !== val && document.activeElement !== el) el.value = val;
        if (k === 'muted' && el.tagName === 'VIDEO') el.muted = true;
      }
    });
    el.__dcAttrs = v.attrs;
  }
  function update(el, v, svg, inst) {
    setAttrs(el, v);
    el.__dcev = v.ev; el.__dcOwner = inst.id;
    if (v.importName) { inst.mountChild(el, v); return; }
    patchChildren(el, v.children, svg || v.tag === 'svg', inst);
    if (v.ref && el.__dcNew) { var f = v.ref; inst.after.push(function () { f(el); }); }
    el.__dcNew = false;
  }
  function same(n, v) {
    if ('text' in v) return n.nodeType === 3;
    return n.nodeType === 1 && n.localName === v.tag && !!n.__dcHost === !!v.importName && (!v.importName || n.__dcHost === v.importName);
  }
  function patchChildren(el, vs, svg, inst) {
    var nodes = Array.prototype.slice.call(el.childNodes);
    var i = 0;
    for (; i < vs.length; i++) {
      var v = vs[i], n = nodes[i];
      if (n && same(n, v)) {
        if ('text' in v) { if (n.nodeValue !== v.text) n.nodeValue = v.text; }
        else update(n, v, svg, inst);
      } else {
        var c = create(v, svg, inst);
        if (n) el.replaceChild(c, n); else el.appendChild(c);
        if (n) inst.unmountWithin(n);
      }
    }
    for (; i < nodes.length; i++) { inst.unmountWithin(nodes[i]); el.removeChild(nodes[i]); }
  }

  function Instance(name, host, props) {
    this.id = ++uid; this.name = name; this.host = host; this.props = props || {}; this.after = []; this.children = [];
    this.pending = false;
    var self = this;
    this.ready = load(name).then(function (def) {
      self.def = def;
      var p = Object.assign({}, def.defaults);
      Object.keys(self.props).forEach(function (k) { p[def.propKeys[k.toLowerCase()] || k] = self.props[k]; });
      self.logic = new def.Comp(p);
      self.logic.__inst = self;
      self.listen();
      self.render();
      if (self.logic.componentDidMount) self.logic.componentDidMount();
      return self;
    });
  }
  Instance.prototype.schedule = function () {
    var self = this;
    if (this.pending || !this.def) return;
    this.pending = true;
    requestAnimationFrame(function () { self.pending = false; self.render(); });
  };
  Instance.prototype.render = function () {
    var vals = this.logic.renderVals ? this.logic.renderVals() : {};
    var out = [];
    build(this.def.tpl, [vals], out, this);
    this.after = [];
    patchChildren(this.host, out, false, this);
    var a = this.after; this.after = [];
    a.forEach(function (f) { try { f(); } catch (e) { console.error(e); } });
  };
  Instance.prototype.setProps = function (props) {
    var def = this.def; if (!def) { this.props = props; return; }
    var p = Object.assign({}, this.logic.props), changed = false;
    Object.keys(props).forEach(function (k) { var kk = def.propKeys[k.toLowerCase()] || k; if (p[kk] !== props[k]) { p[kk] = props[k]; changed = true; } });
    if (changed) { this.logic.props = p; this.schedule(); }
  };
  Instance.prototype.mountChild = function (el, v) {
    el.__dcHost = v.importName;
    if (el.__dcChild) { el.__dcChild.setProps(v.props); return; }
    var child = new Instance(v.importName, el, v.props);
    el.__dcChild = child; this.children.push(child);
  };
  Instance.prototype.unmountWithin = function (n) {
    if (n.nodeType !== 1) return;
    var hosts = n.__dcChild ? [n] : [];
    if (n.querySelectorAll) Array.prototype.push.apply(hosts, n.querySelectorAll('[data-dc-host]'));
    hosts.forEach(function (h) { if (h.__dcChild) { var c = h.__dcChild; c.dead = true; if (c.logic && c.logic.componentWillUnmount) c.logic.componentWillUnmount(); } });
  };
  Instance.prototype.listen = function () {
    var self = this, host = this.host;
    Object.keys(EVENTS).forEach(function (k) {
      var type = EVENTS[k];
      host.addEventListener(type, function (e) {
        var t = e.target;
        if (DIRECT[type]) {
          if (t && t.__dcev && t.__dcOwner === self.id && t.__dcev[type]) fire(t, type, e);
          return;
        }
        while (t && t !== host.parentNode) {
          if (t.__dcev && t.__dcOwner === self.id && t.__dcev[type]) fire(t, type, e);
          if (t === host) break;
          t = t.parentNode;
        }
      }, true);
    });
    function fire(el, type, e) {
      try { Object.defineProperty(e, 'currentTarget', { value: el, configurable: true }); } catch (x) {}
      try { el.__dcev[type](e); } catch (err) { console.error(err); }
    }
  };

  window.DCRuntime = {
    mount: function (name, host, props) { return new Instance(name, host, props); }
  };
})();
