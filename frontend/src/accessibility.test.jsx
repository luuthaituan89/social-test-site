import React from"react";
import{renderToStaticMarkup}from"react-dom/server";
import axe from"axe-core";
import{describe,expect,it}from"vitest";
import{LoadingSkeleton}from"./shared/ui/feedback";

describe("shared UI accessibility",()=>{
  it("has no detectable accessibility violations in the loading state",async()=>{
    document.body.innerHTML=renderToStaticMarkup(<main><h1>SocialN</h1><LoadingSkeleton label="Loading feed"/></main>);
    // jsdom has no canvas implementation, so color contrast remains covered by
    // browser/Lighthouse checks while axe validates the DOM semantics here.
    const result=await axe.run(document.body,{rules:{"color-contrast":{enabled:false}}});
    expect(result.violations).toEqual([]);
  });
});
