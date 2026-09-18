const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const html=fs.readFileSync(require('node:path').join(__dirname,'../dashboard.html'),'utf8');
function logic(){const code=html.match(/<script id="trade-logic">([\s\S]*?)<\/script>/);assert.ok(code,'trade announcement logic exists');const c={};vm.createContext(c);vm.runInContext(code[1],c);return c;}
test('new fills are queued once, HOLD adds nothing, reset clears pending messages',()=>{
 const c=logic(),t=c.makeTradeTracker(),buy={side:'BUY',trade_value:11.66},sell={side:'SELL',trade_value:1};
 t.update({step:1,trade_count:0,trades:[]});assert.equal(t.next(),null);
 t.update({step:3,trade_count:2,trades:[buy,sell]});assert.equal(t.next().side,'BUY');
 t.update({step:3,trade_count:2,trades:[buy,sell]});assert.equal(t.next().side,'SELL');assert.equal(t.next(),null);
 t.update({step:4,trade_count:3,trades:[buy,sell,buy]});t.update({step:0,trade_count:0,trades:[]});assert.equal(t.next(),null);
});
test('opening a running replay shows only its latest historical fill',()=>{const c=logic(),t=c.makeTradeTracker();t.update({step:50,trade_count:2,trades:[{side:'BUY'},{side:'SELL'}]});assert.equal(t.next().side,'SELL');assert.equal(t.next(),null);});
test('announcement uses filled trade value, never fees or requested size',()=>{const c=logic();assert.equal(c.tradeMessage({trade_value:11.658,cost:.0117,requested_value:25}), 'just invested 11.66$ in the opps');});
