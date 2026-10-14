from ticket_agent.airports import format_airports


def test_format_airports_empty():
    assert format_airports([]) == "No airports found."


def test_format_airports_table():
    text = format_airports([
        {"iata": "OSL", "city": "Oslo", "country": "NO", "size": "large", "name": "Oslo Airport, Gardermoen"}
    ])
    assert "OSL" in text and "Oslo Airport, Gardermoen" in text
