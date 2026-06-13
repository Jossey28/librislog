# Homarr

LibrisLog can be integrated into [Homarr](https://homarr.dev/), a modern
dashboard for your self-hosted services, using its
[iframe widget](https://homarr.dev/docs/widgets/iframe/).

This displays your reading statistics as a self-contained stats card on your
Homarr dashboard. Unlike the JSON API integrations, this uses a scoped
**embed token** and requires no custom headers.

## Prerequisites

- A running LibrisLog instance reachable from your Homarr server
- An [embed token](/api/integrations/#embed-tokens) with access to the
  embed widget endpoint
- Embed endpoints must be enabled (default: enabled). To disable, set
  `EMBED_ENABLED=false` in your environment.

## Creating an Embed Token

1. Go to your LibrisLog [Profile](/guide/using-librislog/profile) page.
2. Scroll to the **Embed Tokens** section.
3. Enter a name for your widget (e.g. "Homarr Dashboard").
4. Optionally limit allowed origins for security. For Homarr you can leave
   this empty (wildcard) or set it to your Homarr dashboard URL.
5. Optionally set an expiry date for the token.
6. Click **Add token**.
7. **Copy the displayed token immediately** — it is shown only once.

## Configuration

Add an **iframe widget** to your Homarr dashboard:

1. In Homarr, navigate to your dashboard, click **Edit** → **Add a tile**.
2. Select the **Iframe** widget type.
3. Configure the widget with the following URL:

```
<LIBRISLOG-URL>/embed/v1/stats?token=<EMBED-TOKEN>
```

Replace `<LIBRISLOG-URL>` with your LibrisLog instance URL (e.g.
`https://librislog.example.com`) and `<EMBED-TOKEN>` with the token you
created.

### Customizing the Look

You can add the following optional query parameters to style the widget:

| Parameter | Default | Values | Description |
|-----------|---------|--------|-------------|
| `theme` | `light` | `light`, `dark` | Color theme |
| `accent` | `#3b82f6` | hex color | Accent color for stat numbers |
| `radius` | `md` | `none`, `sm`, `md`, `lg`, `xl` | Card border radius |
| `density` | `normal` | `compact`, `normal`, `comfortable` | Spacing between stat cards |
| `hide_labels` | `false` | `true`, `false` | Hide text labels |
| `show` | all stats | `books`, `reading`, `read`, `to_read`, `pages`, `avg_pages` | Comma-separated list of stat keys to display |
| `lang` | `en` | any language code | HTML `lang` attribute |
| `font_scale` | `1.0` | `0.5`–`3.0` | Font size multiplier |
| `layout` | `grid` | `grid`, `list` | Layout mode |

Example with custom styling:

```
<LIBRISLOG-URL>/embed/v1/stats?token=<EMBED-TOKEN>&theme=dark&accent=%23f59e0b&radius=sm&density=compact&hide_labels=true
```

> **Note:** The accent color must be URL-encoded (e.g. `%23` for `#`).

## How It Works

The embed endpoint (`/embed/v1/stats`) returns a minimal, self-contained HTML
page with your reading statistics. It includes:

- Inline CSS (no external dependencies)
- No-referrer policy and security headers
- No JavaScript, no app shell, no auth redirects

Authentication is handled via the embed token in the query string — no
`X-API-Key` header or browser session required, making it ideal for iframes.

## Security

- Embed tokens are scoped to `embed:stats:read` only — they cannot access
  any other API endpoint.
- Tokens can be revoked or rotated individually from your Profile page.
- If configured, origin restrictions prevent token reuse on unauthorized
  dashboards.
- The embed response does not include the token in the rendered HTML body.
- Response headers include:
  - `Cache-Control: private, max-age=60`
  - `X-Content-Type-Options: nosniff`
  - `Referrer-Policy: no-referrer`
  - `Content-Security-Policy: default-src 'none'; style-src 'unsafe-inline'; frame-ancestors *`
- The embed endpoint can be fully disabled by setting `EMBED_ENABLED=false`.

## Troubleshooting

**Widget shows "Invalid or revoked token"**

- Verify the token was not revoked or rotated.
- Check that the token has not expired.
- Ensure `EMBED_ENABLED` is not set to `false` in your environment.

**Widget returns 403 Forbidden**

- If you configured allowed origins on your token, ensure the `Origin`
  header sent by your dashboard matches one of the listed origins.
- Try removing the allowed origins restriction (set to empty/wildcard)
  for testing.

**Stats are empty (all zeros)**

- The widget displays statistics for the token owner's account. Ensure you
  have added books to your LibrisLog library.

**Widget does not appear or is cut off**

- Adjust the iframe widget size in Homarr. The widget is responsive and
  will fit the available space.
- Try `density=compact` to reduce spacing.
- Try `hide_labels=true` for a more compact display.
- Use `show` to display only the stat keys you need.

**CSP errors in browser console**

- The embed endpoint sets a `Content-Security-Policy` header optimized
  for its minimal HTML. If your dashboard adds a CSP of its own, you may
  need to adjust it to allow inline styles from the iframe.
