self.addEventListener("push", event => {
  let data = {};
  try { data = event.data?.json() || {}; } catch { data = {message: event.data?.text() || "New SocialN notification"}; }
  const title = data.type === "new_message" ? "New SocialN message" : "SocialN";
  const target = data.entity_type === "conversation" ? "/messages" :
    data.entity_type === "chat_group" ? `/messages/group/${data.entity_id}` :
    data.entity_type === "group" ? `/groups/${data.entity_id}` : "/notifications";
  event.waitUntil(self.registration.showNotification(title, {
    body: data.message || "You have a new notification",
    tag: `socialn-${data.type || "notification"}-${data.entity_id || "general"}`,
    data: {url: target},
  }));
});

self.addEventListener("notificationclick", event => {
  event.notification.close();
  const target = new URL(event.notification.data?.url || "/", self.location.origin).href;
  event.waitUntil(clients.matchAll({type: "window", includeUncontrolled: true}).then(windows => {
    const existing = windows.find(client => client.url.startsWith(self.location.origin));
    if (existing) { existing.navigate(target); return existing.focus(); }
    return clients.openWindow(target);
  }));
});
