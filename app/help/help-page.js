/* The app and this page use one versioned Help catalog and renderer. */
(function openFigureToolHelpPage() {
  "use strict";
  // Published browser builds put their editor entry at the package root.
  const packageRoot = new URL("../../", document.baseURI);
  const requestedEditor = new URLSearchParams(location.search).get("editor");
  let returnUrl = packageRoot.href;
  if (requestedEditor) {
    try {
      const candidate = new URL(requestedEditor, document.baseURI);
      if (candidate.origin === packageRoot.origin && candidate.pathname.startsWith(packageRoot.pathname)
          && [packageRoot.pathname, `${packageRoot.pathname}web/`, `${packageRoot.pathname}web/index.html`].includes(candidate.pathname)) returnUrl = candidate.href;
    } catch { /* Keep the package's editor entry. */ }
  }
  const help = globalThis.FigureToolHelp.create({
    pageMode: true,
    helpUrl: "figure-studio-help.json",
    returnUrl,
    openDeepLinkOnCreate: false
  });
  globalThis.FigureToolHelpPage = help;
  const helpLink = globalThis.FigureToolHelp.parseHelpDeepLink(location.hash);
  const retired = globalThis.FigureToolHelp.parseTutorialDeepLink(location.hash);
  void help.open(helpLink?.id || (retired ? globalThis.FigureToolHelp.retiredTopicAlias(retired.tutorialId) : "getting-started"));
})();
