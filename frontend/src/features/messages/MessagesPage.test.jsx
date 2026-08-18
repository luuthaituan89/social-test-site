import React from "react";
import {renderToStaticMarkup} from "react-dom/server";
import {describe,expect,it} from "vitest";
import {MessagesPage} from "./MessagesPage";

describe("MessagesPage mobile state",()=>{
  it("shows the conversation-list state when no conversation is selected",()=>{
    const html=renderToStaticMarkup(<MessagesPage><div>Conversations</div></MessagesPage>);
    expect(html).toContain("mobile-chat-list");
    expect(html).not.toContain("mobile-chat-open");
  });

  it("shows the conversation-detail state after selecting a chat",()=>{
    const html=renderToStaticMarkup(<MessagesPage hasSelection><div>Chat</div></MessagesPage>);
    expect(html).toContain("mobile-chat-open");
  });
});
