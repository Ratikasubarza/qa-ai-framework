from integrations.confluence_client.confluence_client import ConfluenceClient


def test_extract_page_id_from_confluence_url():
    url = "https://thehono.atlassian.net/wiki/spaces/H/pages/37847042/PRD+-+Sprint+3"

    assert ConfluenceClient.extract_page_id(url) == "37847042"


def test_extract_page_id_from_raw_id():
    assert ConfluenceClient.extract_page_id("37847042") == "37847042"


def test_storage_html_to_text_preserves_basic_content():
    html = """
    <h1>PRD - Post Management</h1>
    <p>User can create posts.</p>
    <ul><li>Title is required</li><li>Image is optional</li></ul>
    <table><tr><th>Field</th><th>Rule</th></tr><tr><td>Title</td><td>Required</td></tr></table>
    """

    text = ConfluenceClient.storage_html_to_text(html)

    assert "PRD - Post Management" in text
    assert "User can create posts." in text
    assert "- Title is required" in text
    assert "Field" in text
    assert "Required" in text
