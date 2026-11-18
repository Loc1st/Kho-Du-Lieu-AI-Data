// Real Chrome/Edge smoke test via CDP. Start headless Chrome on port 9222 first.
import fs from 'node:fs';
const target=await fetch('http://127.0.0.1:9222/json/new?about:blank',{method:'PUT'}).then(r=>r.json());
const ws=new WebSocket(target.webSocketDebuggerUrl);
await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject;});
let sequence=0;const pending=new Map(),errors=[];
ws.onmessage=event=>{const msg=JSON.parse(event.data);if(msg.id){const p=pending.get(msg.id);pending.delete(msg.id);msg.error?p.reject(Error(msg.error.message)):p.resolve(msg.result);}else if(msg.method==='Runtime.exceptionThrown')errors.push(msg.params.exceptionDetails);};
function send(method,params={}){return new Promise((resolve,reject)=>{const id=++sequence;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));});}
async function evaluate(expression){const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;}
async function until(expression,timeout=90000){const start=Date.now();while(Date.now()-start<timeout){if(await evaluate(expression))return;await new Promise(r=>setTimeout(r,400));}throw Error('Timed out: '+expression);}
const result={};
try{
 await send('Runtime.enable');await send('Page.enable');
 await send('Emulation.setDeviceMetricsOverride',{width:1440,height:1100,deviceScaleFactor:1,mobile:false});
 await send('Page.navigate',{url:'http://127.0.0.1:8050'});
 await until('document.querySelectorAll("#kpis strong").length===6 && typeof Chart!=="undefined" && Object.keys(Chart.instances).length===6');
 result.initial=await evaluate('({title:document.title,kpis:[...document.querySelectorAll("#kpis strong")].map(x=>x.textContent),charts:Object.values(Chart.instances).map(c=>({id:c.canvas.id,points:c.data.datasets.reduce((n,d)=>n+d.data.length,0),width:c.width,height:c.height}))})');
 if(result.initial.charts.some(c=>c.points===0||c.width===0||c.height===0))throw Error('Empty chart');
 const before=await evaluate('document.querySelectorAll("#kpis strong")[1].textContent');
 await evaluate('(()=>{const s=document.querySelector("select[name=nam]");s.value="2025";s.dispatchEvent(new Event("change"));})()');
 await until('!document.getElementById("status").textContent.includes("Đang truy vấn") && document.querySelectorAll("#kpis strong").length===6');
 result.filtered=await evaluate('({orders:document.querySelectorAll("#kpis strong")[1].textContent,months:Chart.getChart("monthChart").data.labels})');
 if(result.filtered.orders===before||result.filtered.months.some(m=>!m.startsWith('2025')))throw Error('Filter did not update');
 await evaluate('document.querySelector("[data-tab=scd]").click()');
 await until('document.querySelectorAll("#storeHistory tbody tr").length>0');
 result.storeVersions=await evaluate('document.querySelectorAll("#storeHistory tbody tr").length');
 await evaluate('document.querySelector("[data-tab=sql]").click();document.getElementById("executeSql").click()');
 await until('document.querySelectorAll("#sqlResult tbody tr").length>0');
 result.sql=await evaluate('document.getElementById("sqlTiming").textContent');
 await evaluate('document.querySelector("[data-tab=etl]").click()');
 await until('document.querySelectorAll("#etlLogs tbody tr").length>0');
 result.etlRows=await evaluate('document.querySelectorAll("#etlLogs tbody tr").length');
 result.testRows=await evaluate('document.querySelectorAll("#testResults tbody tr").length');
 result.benchmarkRows=await evaluate('document.querySelectorAll("#benchmark tbody tr").length');
 if(result.testRows!==10||result.benchmarkRows!==5)throw Error('Missing live ETL reports');
 await evaluate('document.querySelector("[data-tab=dashboard]").click()');
 await until('document.querySelectorAll("#kpis strong").length===6 && !document.getElementById("status").textContent.includes("Đang truy vấn")');
 const screenshot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});
 fs.writeFileSync('output/phone_sales/dashboard.png',Buffer.from(screenshot.data,'base64'));
 await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
 await new Promise(r=>setTimeout(r,600));
 result.mobile=await evaluate('({width:innerWidth,body:document.documentElement.scrollWidth})');
 if(result.mobile.body>result.mobile.width+1)throw Error('Mobile horizontal overflow');
 await evaluate(`window.originalFetch=window.fetch;window.fetch=()=>Promise.resolve(new Response(JSON.stringify({error:'Kiểm thử API không khả dụng'}),{status:503,headers:{'Content-Type':'application/json'}}));document.querySelector('select[name=nam]').dispatchEvent(new Event('change'))`);
 await until('document.getElementById("status").classList.contains("error")');
 result.apiErrorState=await evaluate('({message:document.getElementById("status").textContent,kpis:document.querySelectorAll("#kpis strong").length,charts:Object.keys(Chart.instances).length})');
 if(result.apiErrorState.kpis!==0||result.apiErrorState.charts!==0)throw Error('Stale data visible after API failure');
 await evaluate('window.fetch=window.originalFetch;document.querySelector("select[name=nam]").dispatchEvent(new Event("change"))');
 await until('document.querySelectorAll("#kpis strong").length===6 && Object.keys(Chart.instances).length===6');
 result.javascriptErrors=errors;
 if(errors.length)throw Error('Browser JavaScript exception');
 result.status='PASS';
}catch(e){result.status='FAIL';result.error=String(e);result.javascriptErrors=errors;process.exitCode=1;}
finally{fs.writeFileSync('output/phone_sales/browser_smoke.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result,null,2));ws.close();}
