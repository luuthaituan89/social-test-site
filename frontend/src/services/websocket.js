import{authService}from"./auth";
import{WS_BASE_URL}from"./api";

export function createAuthenticatedSocket(path){
  const separator=path.includes("?")?"&":"?";
  return new WebSocket(`${WS_BASE_URL}${path}${separator}token=${encodeURIComponent(authService.token()||"")}`);
}

export function openRealtimeChannel(path,{onMessage,onOpen,onClose,onError}={}){
  const socket=createAuthenticatedSocket(path);
  if(onOpen)socket.addEventListener("open",onOpen);
  if(onMessage)socket.addEventListener("message",onMessage);
  if(onClose)socket.addEventListener("close",onClose);
  if(onError)socket.addEventListener("error",onError);
  return()=>socket.close();
}
