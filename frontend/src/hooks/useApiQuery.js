import{useQuery}from"@tanstack/react-query";
import{apiClient}from"../services/api";

export function useApiQuery(queryKey,path,options={}){
  return useQuery({queryKey,queryFn:()=>apiClient(path),...options});
}
