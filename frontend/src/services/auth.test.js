import{beforeEach,describe,expect,it}from"vitest";
import{authService}from"./auth";

describe("authService",()=>{
  beforeEach(()=>{localStorage.clear();authService.clear()});
  it("stores and clears the session token",()=>{
    authService.saveToken("token-1");
    expect(authService.token()).toBe("token-1");
    expect(authService.isAuthenticated()).toBe(true);
    authService.clear();
    expect(authService.isAuthenticated()).toBe(false);
  });
});
