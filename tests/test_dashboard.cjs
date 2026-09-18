const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
test('chart shows only fly equity and ignores baseline when scaling',()=>{
 const page=fs.readFileSync(require('node:path').join(__dirname,'../dashboard.html'),'utf8');
 const source=page.slice(page.indexOf('function draw('),page.indexOf('function render('));
 const chart={innerHTML:''},ctx=vm.createContext({$:()=>chart});vm.runInContext(source,ctx);
 ctx.draw([{equity:100,baseline:100},{equity:103,baseline:10000}]);
 assert.equal((chart.innerHTML.match(/<polyline/g)||[]).length,1);
 const first=chart.innerHTML;
 ctx.draw([{equity:100,baseline:100},{equity:103,baseline:1}]);assert.equal(chart.innerHTML,first);
 assert.ok(!page.includes('<span>Buy & hold</span>'));
});
test('dashboard P&L uses $10,000 capital and reset shows the new limits',()=>{
 const page=fs.readFileSync(require('node:path').join(__dirname,'../dashboard.html'),'utf8');
 const els={};const get=id=>els[id]??=( {style:{},children:[],textContent:''} );
 const ctx=vm.createContext({$:get,draw:()=>{},updateAnnouncements:()=>{},money:v=>'$'+Number(v).toFixed(2),num:String});
 vm.runInContext(page.slice(page.indexOf('function render('),page.indexOf('async function refresh(')),ctx);
 ctx.render({status:'ready',starting_cash:10000});
 assert.equal(get('equity').textContent,'$10000.00');
 assert.ok(get('order-size').textContent.includes('$250'));
 ctx.render({status:'ready',starting_cash:10000,equity:9999,baseline:10000,price:50,date:'test',neural:{memory:{changed_edges:0}},activity:[],range:['test'],shares:0,cash:9999,trades:[],costs:0,source:'test',fetched_at:'test'});
 assert.equal(get('pnl').textContent,'$-1.00 since start');
 assert.equal(get('pnl').className,'sub negative');
});
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
