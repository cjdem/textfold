# Security

## Reporting a problem

Please do not open a public issue for a security problem. Report it privately through GitHub: the repository's
**Security** tab, **Report a vulnerability**. Please allow a few days for an answer. Once a fix is released, the report
is published, with credit to you if you wish.

## What TextFold guards

TextFold runs on your own computer and reads text from places it does not control. It is built so that this text
cannot act on your computer, and so that it cannot steer the model that folds it:

- The local server listens on 127.0.0.1 only, and refuses a POST from another page: when a writing POST carries an
  Origin, it must be this server's own local name and port, so another site — or another page on a different
  localhost port — cannot drive it. A request with no Origin is a command line or a native client, not a page. It
  answers only requests addressed to this computer's own names (localhost, 127.0.0.1, [::1]), so a site that points
  its own domain at this computer (DNS rebinding) cannot read the library either.
- Text from Europe PMC, bioRxiv, medRxiv, Wikipedia, GitHub READMEs, Markdown files, web pages and converted PDFs
  passes through an allowlist before the reader shows it: no script, no event handler, no `javascript:` link, no
  frame, no form, no embedded object.
- A document's pictures are served by the app at their own address; an SVG drawing stays inside its page instead,
  since an SVG served from the app's own address could run script there.
- On a web page, text hidden from its readers (`display: none`, `hidden`, `aria-hidden`, screen-reader classes,
  zero-size text) is removed before a model sees the page, and the model is told that an instruction inside a
  document is part of what the document says, never to be followed.
- Keys and settings are kept in `~/.textfold/settings.json`, readable by you alone, never in the project folder.
- A key TextFold keeps — a provider's saved key, or the OpenRouter key made by one-click authorisation — is sent only
  to the address it was saved for. A probe may carry the caller's own key to another address, but never one the server
  holds.
- PDFs and pictures are sent to the MinerU API address in Settings (MinerU's official address by default) for
  conversion. The file leaves your computer for that conversion, and the page says so before it is sent. The API key
  is kept in `~/.textfold/settings.json`.

A known gap: arXiv's HTML is shown as LaTeXML wrote it, without the allowlist. Rules made for LaTeXML (its drawings
and sizes must survive them) are in progress. A page can also call the OpenRouter return (`/oauth/openrouter`, a GET)
and use up a pending authorisation: it never sees the key, and the reader can start again.

## In scope

The local server and its API, the reader, the import of every source, and the MinerU Cloud API conversion.
Problems in the models TextFold calls, or in the sites it reads from, belong to them.
