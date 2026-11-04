# Sending the Kubeerra Market Brief

Each issue produces these files (in `out/<date>/` during the run, and in `deliverables/` on
GitHub, where the 14 most recent issues are kept):

- `kubeerra-market-brief-<date>-gmail.html`: the email for Gmail (navy masthead and footer).
- `kubeerra-market-brief-<date>-outlook.html`: the email for Outlook, classic, new or on the web
  (light masthead and footer, so it stays readable if Outlook drops text colours on paste).
- `kubeerra-market-brief-<date>.pdf`: the A4 edition, attached to the email and archived.
- The WhatsApp card (PNG, 1080 by 1920) and the WhatsApp message to send with it, and the
  plain-text edition.

The morning run also leaves an unsent Gmail draft with the email already in it (D-043). Its logo
is checked byte for byte after saving (D-056); if the check failed three times the draft shows a
lettered gold K tile instead of the image, never a broken picture.

## Looking at the email before sending

The preview inside the Claude app cannot load images hosted on the web, so the logo looks
missing there even when it is fine. To see the email as readers will, open the Gmail preview
image the run sends (gmail-desktop.png), the Gmail draft, or the HTML file downloaded and opened
in Chrome or Edge.

## Before sending

1. Open the check report: it must contain no FAIL lines.
2. Confirm the headline figures listed under "Figures to confirm" against their sources.
3. Read the email once in the browser or in the Gmail draft.

## Gmail

Easiest: open Gmail, go to Drafts, open the draft titled with the day's subject line, add the
recipients (Bcc for a client list), attach the PDF and send. The run checked every number in
the draft against the Gmail file; if it could not, it deleted the draft and said so.

By hand: open the Gmail file in Chrome, press Ctrl+A and Ctrl+C, paste into a new Gmail
message, paste the suggested subject line (first line of the check report) and attach the PDF.
Gmail only shows images at a public web address, so the logo is hosted on Vercel.

## Outlook (classic, new Outlook and Outlook on the web)

1. Open the Outlook file in Microsoft Edge or Google Chrome.
2. Press Ctrl+A, then Ctrl+C.
3. In Outlook, start a new message, click in the body and press Ctrl+V.
4. Paste the suggested subject line and attach the PDF.
5. Send it to yourself first and open it on your phone.

Outlook may drop text colours when it pastes. The Outlook file is built for that: every line of
text sits on a white or pale background, so it stays readable in black, and rises and falls
keep their ▲ and ▼ markers. Do not paste the Gmail file into Outlook.

Some classic Outlook builds also offer Insert > Attach File > Insert as Text for an HTML file,
which carries the HTML across unchanged. Use it if your version shows that option.

## Links

Readers' links go only to kubeerra.com pages and the firm's email address (D-039). Outside
sources are named in the text without links; their addresses stay in the issue file and the
check report for verification.

## Known differences between clients

- Classic Outlook ignores rounded corners and some letter spacing; the layout holds.
- Gmail clips messages above about 102 KB, which would hide the disclosures at the bottom; the
  check script keeps the Gmail file under 96 KB. Outlook does not clip, but Word adds its own
  markup when you paste, so a Gmail reader of an Outlook-sent copy may see "View entire
  message"; the PDF carries the complete issue either way.
- The contents list links to each part within the email. Gmail on the web and Outlook follow
  them; some phone apps do not, and simply ignore the links.
- Some phone apps tint backgrounds in dark mode; the emails ask for the light scheme.

## WhatsApp

Send the card first, then paste the WhatsApp message file as the next message. The message opens
with the registered name and ARN (SEBI's social media disclosure rule) and ends with the short
disclaimer, the standard warning and the link to the full disclaimer on kubeerra.com. FII and DII
flows are in the message, not on the card (D-054). Forward the card and message together, never
the card with the message removed.
