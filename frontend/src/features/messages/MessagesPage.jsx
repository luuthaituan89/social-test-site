export function MessagesPage({children,hasSelection=false}){
  return <section className={`chat-layout ${hasSelection?"mobile-chat-open":"mobile-chat-list"}`} data-module="messages">{children}</section>
}
