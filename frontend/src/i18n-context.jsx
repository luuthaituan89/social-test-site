import React,{createContext,useCallback,useContext,useEffect,useMemo,useState}from"react";
import{getSiteLanguage,normalizeLanguage,setSiteLanguage,translate}from"./i18n";

const I18nContext=createContext(null);

function initialLanguage(){
  if(typeof localStorage!=="undefined"){
    const saved=localStorage.getItem("socialn_language");
    if(saved)return normalizeLanguage(saved);
  }
  if(typeof navigator!=="undefined")return normalizeLanguage(navigator.language?.slice(0,2));
  return getSiteLanguage();
}

export function I18nProvider({children,initialLocale}){
  const[language,setLanguageState]=useState(()=>normalizeLanguage(initialLocale||initialLanguage()));
  useEffect(()=>{setSiteLanguage(language)},[language]);
  const setLanguage=useCallback(locale=>setLanguageState(normalizeLanguage(locale)),[]);
  const t=useCallback((key,params={})=>translate(key,params,language),[language]);
  const value=useMemo(()=>({language,setLanguage,t}),[language,setLanguage,t]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(){
  const value=useContext(I18nContext);
  if(!value)throw new Error("useI18n must be used inside I18nProvider");
  return value;
}

export function Trans({id,values,as:Element="span",...props}){
  const{t}=useI18n();
  return <Element {...props}>{t(id,values)}</Element>;
}
