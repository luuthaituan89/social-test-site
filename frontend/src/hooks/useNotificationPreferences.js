import{useEffect,useState}from"react";

export const NOTIFICATION_DEFAULTS={enabled:true,desktop:true,sound:true,preview:"full",duration:6000};

function read(){
  try{return{...NOTIFICATION_DEFAULTS,...JSON.parse(localStorage.getItem("socialn_message_notifications")||"{}")}}
  catch{return{...NOTIFICATION_DEFAULTS}}
}

export function useNotificationPreferences(){
  const[preferences,setPreferences]=useState(read);
  useEffect(()=>localStorage.setItem("socialn_message_notifications",JSON.stringify(preferences)),[preferences]);
  return[preferences,setPreferences];
}
