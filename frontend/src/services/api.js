import{authService}from"./auth";

export const API_BASE_URL=import.meta.env.VITE_API_URL||"http://localhost:8000";
export const WS_BASE_URL=API_BASE_URL.replace(/^http/,"ws");

export function assetUrl(value){
  if(!value)return null;
  return /^https?:\/\//i.test(value)?value:`${API_BASE_URL}${value}`;
}

export function apiError(detail){
  if(Array.isArray(detail))return detail.map(item=>item?.msg||String(item)).join("; ");
  if(detail&&typeof detail==="object")return detail.message||JSON.stringify(detail);
  return detail||"Request failed";
}

export async function apiClient(path,options={}){
  const request=async()=>{const headers=new Headers(options.headers||{}),token=authService.token();
  if(token)headers.set("Authorization",`Bearer ${token}`);
  if(!(options.body instanceof FormData)&&options.body!==undefined)headers.set("Content-Type","application/json");
  return fetch(`${API_BASE_URL}${path}`,{...options,headers,credentials:"include"})};
  let response=await request();
  const authRoute=path.startsWith("/api/auth/login")||path.startsWith("/api/auth/register")||path.startsWith("/api/auth/refresh")||path.startsWith("/api/auth/forgot-password")||path.startsWith("/api/auth/reset-password")||path.startsWith("/api/auth/email/verify");
  if(response.status===401&&!authRoute&&options.authRetry!==false){try{await authService.refresh();response=await request()}catch{authService.clear()}}
  const data=await response.json().catch(()=>({}));
  if(response.status===401)window.dispatchEvent(new CustomEvent("socialn:unauthorized"));
  if(!response.ok)throw Error(apiError(data.detail));
  return data;
}
