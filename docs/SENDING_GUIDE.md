# Sending the Kubeerra Market Brief

Each issue produces two files in `out/<date>/`:

- `kubeerra-market-brief-<date>.html`: the email, built for classic Outlook, the new Outlook,
  Outlook on the web and Gmail.
- `kubeerra-market-brief-<date>.pdf`: the A4 edition, attached to the email and archived.

## Before sending

1. Open `check-report.md`: it must contain no FAIL lines.
2. Confirm the headline figures listed under "Figures to confirm" against their sources.
3. Open the HTML in Chrome or Edge and read it through once.

## Classic Outlook for Windows

1. Open the HTML file in Microsoft Edge or Google Chrome.
2. Press Ctrl+A, then Ctrl+C.
3. In Outlook, start a new message, click in the body and press Ctrl+V.
4. Paste the suggested subject line (first line of the check report) and attach the PDF.
5. Send it to yourself first and open it on your phone, then send it to the RM team.

Some Outlook builds also offer Insert > Attach File > Insert as Text for an HTML file,
which carries the HTML across unchanged. Use it if your version shows that option.

## New Outlook and Outlook on the web

Use the same browser copy and paste. Outlook on the web keeps the inline styles.

## Gmail

Open the HTML in Chrome, press Ctrl+A and Ctrl+C, then paste into a new Gmail message and
attach the PDF. Gmail only shows images that live at a public web address, so the logo
must be hosted (Vercel for now).

## Known differences between clients

- Classic Outlook ignores rounded corners and some letter spacing; the layout holds.
- Gmail clips messages above about 102 KB; the check script keeps issues under 90 KB.
- Some phone apps tint backgrounds in dark mode; the email asks for the light scheme.
- The first pilot issue should be test-sent once to each client in use, and any
  difference noted in the project record.
