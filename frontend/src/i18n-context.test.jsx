import React from"react";
import{renderToStaticMarkup}from"react-dom/server";
import{describe,expect,it}from"vitest";
import{I18nProvider,useI18n}from"./i18n-context";
import{LANGUAGES,missingTranslations}from"./i18n";

function Example(){const{language,t}=useI18n();return <p lang={language}>{t("Settings")}</p>}

describe("I18nProvider",()=>{
  it("translates during React rendering without mutating DOM text",()=>{
    const html=renderToStaticMarkup(<I18nProvider initialLocale="vi"><Example/></I18nProvider>);
    expect(html).toContain("Cài đặt");
    expect(html).toContain('lang="vi"');
  });
  it("reports missing translation keys deterministically",()=>{
    for(const locale of LANGUAGES)expect(missingTranslations(locale.code)).toEqual([]);
  });
});
