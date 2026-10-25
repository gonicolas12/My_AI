/* ═══════════════════════════════════════════════════ */
/* My_AI Relay — Langue de la page mobile               */
/*                                                       */
/* La page parle la langue de My_AI sur le PC (réglage   */
/* language.default) : le Relay injecte la langue et son */
/* catalogue (relay/static/locales/), complété par       */
/* l'anglais puis le français pour une clé absente.      */
/* Clé à points → texte, {paramètres} remplacés ; pour   */
/* un nombre ({count}), forme du pluriel selon la langue.*/
/* Les éléments du HTML portent leur clé : data-i18n     */
/* (texte), data-i18n-placeholder, -title, -aria-label.  */
/* ═══════════════════════════════════════════════════ */

(function () {
  'use strict';

  var catalog = {};
  try {
    var data = document.getElementById('relayI18n');
    catalog = data ? JSON.parse(data.textContent || '{}') : {};
  } catch (e) {
    catalog = {};
  }
  var lang = document.documentElement.lang || 'fr';
  // Chiffres latins en arabe, comme les nombres insérés dans les textes
  var locale = lang === 'ar' ? 'ar-u-nu-latn' : lang;
  var rules = null;
  try {
    rules = new Intl.PluralRules(locale);
  } catch (e) {
    rules = null;
  }

  function t(key, params) {
    var message = catalog[key];
    if (message === undefined || message === null) return key;
    var text = message;
    if (typeof message === 'object') {
      var count = Number(params && params.count) || 0;
      var category = rules ? rules.select(count) : (count === 1 ? 'one' : 'other');
      text = message[category] || message.other || '';
    }
    if (!params) return String(text);
    return String(text).replace(/\{(\w+)\}/g, function (match, name) {
      return Object.prototype.hasOwnProperty.call(params, name) ? String(params[name]) : match;
    });
  }

  function apply(root) {
    var scope = root || document;
    scope.querySelectorAll('[data-i18n]').forEach(function (node) {
      node.textContent = t(node.getAttribute('data-i18n'));
    });
    ['placeholder', 'title', 'aria-label'].forEach(function (attr) {
      scope.querySelectorAll('[data-i18n-' + attr + ']').forEach(function (node) {
        node.setAttribute(attr, t(node.getAttribute('data-i18n-' + attr)));
      });
    });
  }

  window.RelayI18n = { t: t, apply: apply, lang: lang, locale: locale };
  apply(document);
})();
