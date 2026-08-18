import{useEffect}from"react";
import{openRealtimeChannel}from"../services/websocket";

export function useRealtimeChannel(path,handlers={},enabled=true){
  useEffect(()=>{
    if(!enabled)return undefined;
    return openRealtimeChannel(path,handlers);
  },[path,enabled,handlers.onMessage,handlers.onOpen,handlers.onClose,handlers.onError]);
}
