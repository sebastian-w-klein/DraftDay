from app.parsers.static_html import GenericStaticHtmlParser


def test_parse_table_picks_and_metadata() -> None:
    parser = GenericStaticHtmlParser(
        source_slug="espn",
        title_selectors=("h1",),
        author_selectors=("meta[name='author']",),
        published_at_selectors=("meta[property='article:published_time']",),
    )
    html = """
    <html>
      <head>
        <meta name="author" content="Analyst Name" />
        <meta property="article:published_time" content="2026-04-01T12:00:00Z" />
      </head>
      <body>
        <h1>2026 NFL Mock Draft 1.0</h1>
        <table>
          <tr><th>Pick</th><th>Team</th><th>Player</th></tr>
          <tr><td>1</td><td>Tennessee Titans</td><td>Cam Ward, QB, Miami</td></tr>
          <tr><td>2</td><td>Cleveland Browns</td><td>Travis Hunter, WR, Colorado</td></tr>
        </table>
      </body>
    </html>
    """
    parsed = parser.parse_metadata(html, "https://example.com/mock")
    picks = parser.parse_picks(html)
    assert parsed["title"] == "2026 NFL Mock Draft 1.0"
    assert parsed["author_name"] == "Analyst Name"
    assert parsed["draft_year"] == 2026
    assert len(picks) == 2
    assert picks[0]["player_name"] == "Cam Ward"


def test_parse_list_fallback_when_no_table() -> None:
    parser = GenericStaticHtmlParser(source_slug="nfl-com")
    html = """
    <html>
      <body>
        <h1>Mock Draft</h1>
        <ol>
          <li>1. Tennessee Titans - Cam Ward, QB, Miami</li>
          <li>2. Cleveland Browns - Travis Hunter, WR, Colorado</li>
        </ol>
      </body>
    </html>
    """
    picks = parser.parse_picks(html)
    assert len(picks) == 2
    assert picks[1]["overall_pick"] == 2
    assert picks[1]["player_name"] == "Travis Hunter"
