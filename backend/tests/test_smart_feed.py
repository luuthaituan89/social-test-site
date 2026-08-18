from datetime import datetime, timedelta

from app.services.feed import decode_cursor, diversify, encode_cursor, score_post


def test_relationship_and_favorite_raise_feed_score():
    created = datetime.utcnow() - timedelta(hours=2)
    ordinary = score_post(created_at=created, reactions=3, comments=1,
                          is_friend=False, is_following=False, is_favorite=False,
                          viewer_interacted=False, show_fewer_author=False)
    close = score_post(created_at=created, reactions=3, comments=1,
                       is_friend=True, is_following=True, is_favorite=True,
                       viewer_interacted=True, show_fewer_author=False)
    assert close > ordinary


def test_show_fewer_penalizes_author():
    created = datetime.utcnow()
    normal = score_post(created_at=created, reactions=0, comments=0,
                        is_friend=False, is_following=False, is_favorite=False,
                        viewer_interacted=False, show_fewer_author=False)
    reduced = score_post(created_at=created, reactions=0, comments=0,
                         is_friend=False, is_following=False, is_favorite=False,
                         viewer_interacted=False, show_fewer_author=True)
    assert reduced < normal


def test_diversity_caps_authors_and_duplicate_shared_sources():
    rows = [
        {"id": 1, "author_id": 7, "shared_post_id": None},
        {"id": 2, "author_id": 7, "shared_post_id": None},
        {"id": 3, "author_id": 7, "shared_post_id": None},
        {"id": 4, "author_id": 8, "shared_post_id": 99},
        {"id": 5, "author_id": 9, "shared_post_id": 99},
        {"id": 6, "author_id": 9, "shared_post_id": None},
    ]
    result = diversify(rows, 4, max_per_author=2)
    assert len(result) == 4
    assert [row["author_id"] for row in result[:3]] != [7, 7, 7]
    assert sum(row["shared_post_id"] == 99 for row in result[:3]) <= 1


def test_cursor_round_trip_and_invalid_cursor():
    assert decode_cursor(encode_cursor([1, 2, 3])) == {1, 2, 3}
    assert decode_cursor("not-a-cursor") == set()
