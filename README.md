# Kubeerra Market Brief

A daily pre-market newsletter for Kubeerra, the digital brand of Dhariwal Securities Private
Limited (AMFI-registered Mutual Fund Distributor, ARN-369716). One structured issue file is
rendered to email HTML (classic Outlook, new Outlook, Outlook on the web, Gmail), an A4 PDF, a
plain-text alternative and a WhatsApp snapshot card.

Status: RM pilot in preparation. Owner and approver: Shriansh Jena.

## Layout

    CLAUDE.md                       rules for any Claude session working here
    docs/                           editorial standards, sending guide, agent rules, project record
    .claude/skills/daily-market-report/   the daily procedure
    .claude/agents/                 four gatherers, a compliance reviewer, a fact-checker
    design-tokens/tokens.json       colours, fonts, spacing (navy, cobalt, teal)
    config/publication.json         legal lines, disclosures, contacts, asset locations
    schema/issue.schema.json        the contract every issue file meets
    issues/                         one JSON file per issue
    templates/                      email, PDF and card templates
    render/                         the build script and number formatting
    checks/                         automated checks and the review report
    learn/                          the learning library
    hosting/                        static files for the email logo (deploy to Vercel)
    tests/fixture-issue.json        synthetic issue for template tests (not real data)

## Commands

    pip install jinja2 jsonschema weasyprint pypdf pillow     # plus poppler-utils for previews
    python3 render/build.py issues/2026-10-29.json --logo-url https://<host>/logo/kubeerra-tile-96.png
    python3 checks/check_issue.py issues/2026-10-29.json

Outputs land in `out/<date>/` (not committed).

## Fonts

General Sans (Fontshare, ITF EULA) is the intended face. Until its files are added to
`assets/fonts/` as `GeneralSans-Regular.otf` and similar, the PDF uses Hanken Grotesk.
JetBrains Mono (OFL) is used for labels. Email uses system fonts by design.
