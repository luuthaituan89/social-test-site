import {apiClient as api} from "./api";

function decodeKey(value){
  const padding="=".repeat((4-value.length%4)%4),raw=atob((value+padding).replace(/-/g,"+").replace(/_/g,"/"));
  return Uint8Array.from([...raw].map(char=>char.charCodeAt(0)));
}

export async function pushStatus(){
  if(!("serviceWorker" in navigator)||!("PushManager" in window))return{supported:false,subscribed:false};
  const config=await api("/api/notifications/push/public-key");
  const registration=await navigator.serviceWorker.register("/sw.js");
  const subscription=await registration.pushManager.getSubscription();
  return{supported:true,configured:config.enabled,subscribed:Boolean(subscription),permission:Notification.permission};
}

export async function enablePush(){
  const config=await api("/api/notifications/push/public-key");
  if(!config.enabled)throw Error("Web Push keys have not been configured on the server.");
  const permission=await Notification.requestPermission();
  if(permission!=="granted")throw Error("Notification permission was not granted.");
  const registration=await navigator.serviceWorker.register("/sw.js");
  let subscription=await registration.pushManager.getSubscription();
  if(!subscription)subscription=await registration.pushManager.subscribe({userVisibleOnly:true,applicationServerKey:decodeKey(config.public_key)});
  const value=subscription.toJSON();
  await api("/api/notifications/push/subscriptions",{method:"POST",body:JSON.stringify({endpoint:value.endpoint,p256dh:value.keys.p256dh,auth:value.keys.auth})});
  return pushStatus();
}

export async function disablePush(){
  const registration=await navigator.serviceWorker.getRegistration();
  const subscription=await registration?.pushManager.getSubscription();
  if(subscription){
    await api(`/api/notifications/push/subscriptions?endpoint=${encodeURIComponent(subscription.endpoint)}`,{method:"DELETE"});
    await subscription.unsubscribe();
  }
  return pushStatus();
}
