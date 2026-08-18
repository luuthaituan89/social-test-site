const API_BASE_URL=import.meta.env.VITE_API_URL||"http://localhost:8000";
let accessToken=null;
let refreshPromise=null;

// Consume the legacy persistent token once. New tokens remain in memory and
// are restored through the HttpOnly refresh cookie after a page reload.
const legacy=localStorage.getItem("socialn_token");
if(legacy){accessToken=legacy;localStorage.removeItem("socialn_token")}

export const authService={
  token:()=>accessToken,
  isAuthenticated:()=>Boolean(accessToken),
  saveToken(token){accessToken=token||null},
  clear(){accessToken=null;localStorage.removeItem("socialn_token")},
  async refresh(){
    if(refreshPromise)return refreshPromise;
    refreshPromise=fetch(`${API_BASE_URL}/api/auth/refresh`,{method:"POST",credentials:"include"})
      .then(async response=>{if(!response.ok)throw Error("Session expired");const data=await response.json();accessToken=data.access_token;return data})
      .catch(error=>{accessToken=null;throw error})
      .finally(()=>{refreshPromise=null});
    return refreshPromise;
  },
  async restore(){if(accessToken)return{access_token:accessToken};return this.refresh()}
};
