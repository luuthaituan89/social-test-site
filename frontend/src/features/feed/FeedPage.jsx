export function FeedPage({composer,posts,empty}){return <section className="feed-page" data-module="feed">{composer}{posts.length?posts:empty}</section>}
