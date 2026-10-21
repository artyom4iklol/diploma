import fs from 'node:fs/promises';
import path from 'node:path';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

// Run with the bundled Node runtime from a writable temp directory whose
// node_modules symlink points to CODEX_PRIMARY_RUNTIME_NODE_MODULES.
const [specPath, outputDir] = process.argv.slice(2);
if (!specPath || !outputDir) throw new Error('Usage: node build_graph_workbook.mjs spec.json output_dir');
const spec = JSON.parse(await fs.readFile(specPath, 'utf8'));
await fs.mkdir(outputDir, { recursive: true });
const previewDir = path.join(outputDir, 'previews');
await fs.mkdir(previewDir, { recursive: true });
const wb = Workbook.create();
const col = n => { let s=''; for (;n; n=Math.floor((n-1)/26)) s=String.fromCharCode(65+(n-1)%26)+s; return s; };
const numericFmt = '#,##0.00;[Black]-#,##0.00;0.00';
const checks = [], expected = [], renders = [], sections = [];
for (const s of spec.sheets) wb.worksheets.add(s.name);

for (const def of spec.sheets) {
  const sh = wb.worksheets.getItem(def.name);
  const last = Math.max(...def.sections.map(t => t.header_row+t.rows.length));
  const cols = Math.max(...def.sections.map(t => t.headers.length));
  const widths = {};
  for (const t of def.sections) for (const [k,v] of Object.entries(t.widths)) widths[k]=Math.max(widths[k]||0,v);
  // Keep the index readable; its long instructions wrap below the catalogue.
  if (def.name==='Оглавление') widths[2]=62;
  sh.showGridLines = false;
  const used=sh.getRange(`A1:${col(cols)}${last}`);
  used.format.font={name:'Arial',size:11,color:'#111111'};
  used.format.verticalAlignment='center';
  used.format.rowHeight=22;
  for(let c=1;c<=cols;c++) sh.getRange(`${col(c)}1:${col(c)}${last}`).format.columnWidth=widths[c]||24;
  sh.getRange('A1').format.rowHeight=8;
  sh.getRange('A2').values=[[def.title]];
  sh.getRange('A2').format.font={name:'Arial',size:15,bold:true,color:'#111111'};
  sh.getRange(`A2:${col(cols)}2`).format.rowHeight=29;
  sh.getRange(`A2:${col(cols)}2`).format.borders={bottom:{style:'thin',color:'#777777'}};
  const totalWidth=Object.values(widths).reduce((a,b)=>a+b,0);
  const lineLength=Math.max(75,Math.floor(totalWidth*.92));
  const wrap = str => {
    const words=str.split(' '),lines=[]; let ln='';
    for(const w of words){if((ln+' '+w).length>lineLength){lines.push(ln);ln=w;}else ln+=(ln?' ':'')+w;}
    if(ln)lines.push(ln); return lines.join('\n');
  };
  sh.getRange('A3').values=[[wrap(def.note)]];
  sh.getRange('A3').format.font={name:'Arial',size:11,italic:true,color:'#444444'};
  sh.getRange(`A3:${col(cols)}3`).format.rowHeight=22*wrap(def.note).split('\n').length;
  sh.getRange('A4').values=[[def.source ? `Источник: ${def.source}` : '']];
  sh.getRange('A4').format.font={name:'Arial',size:11,color:'#555555'};
  if(last>25)sh.freezePanes.freezeRows(6);
  if(cols>8)sh.freezePanes.freezeColumns(1);
  if(def.name==='Оглавление')sh.tabColor='#333333';
  if(def.name==='Данные')sh.tabColor='#888888';
  for(const t of def.sections){
    const r=t.header_row, n=t.rows.length, end=col(t.headers.length);
    sh.getRange(`A${r-1}`).values=[[t.label]];
    sh.getRange(`A${r-1}`).format.font={name:'Arial',size:11,bold:true,color:'#111111'};
    sh.getRange(`A${r-1}:${end}${r-1}`).format.rowHeight=26;
    const head=sh.getRange(`A${r}:${end}${r}`);
    head.values=[t.headers];
    head.format={fill:'#E7E7E7',font:{name:'Arial',size:11,bold:true,color:'#111111'},wrapText:true,horizontalAlignment:'center',verticalAlignment:'center',borders:{bottom:{style:'thin',color:'#555555'}}};
    head.format.rowHeight=Math.max(36,...t.headers.map((v,i)=>Math.ceil(v.length/((widths[i+1]||24)*.86))*16+8));
    const vals=t.rows.map(row=>row.map(v=>v && typeof v==='object' ? ('date' in v ? new Date(v.date+'T00:00:00Z') : null):v));
    const range=sh.getRange(`A${r+1}:${end}${r+n}`);
    range.values=vals;
    range.format.horizontalAlignment='left';
    range.format.wrapText=true;
    for(let i=0;i<n;i++){
      let h=22;
      for(let j=0;j<t.headers.length;j++){
        const v=t.rows[i][j]; const cell=`${col(j+1)}${r+i+1}`;
        if(v && typeof v==='object' && v.formula){
          sh.getRange(cell).formulas=[[v.formula]];
          expected.push({sheet:def.name,cell,value:v.expected});
        }
        if(typeof v==='string')h=Math.max(h,Math.ceil(v.length/((widths[j+1]||24)*.86))*15+5);
        if(typeof v==='number'||(v&&typeof v==='object'))sh.getRange(cell).format.horizontalAlignment='right';
      }
      sh.getRange(`A${r+i+1}:${end}${r+i+1}`).format.rowHeight=h;
    }
    for(const [c,fmt] of Object.entries(t.formats))sh.getRange(`${col(+c)}${r+1}:${col(+c)}${r+n}`).setNumberFormat(fmt);
    sections.push({sheet:def.name,range:`A${r+1}:${end}${r+n}`,row:r+1,colCount:t.headers.length,rows:t.rows});
  }
  renders.push({sheet:def.name,range:`A1:${col(cols)}${Math.min(last,14)}`});
  console.log(`Built ${def.name}`);
}

wb.recalculate();
// Compare every formula to an independent numerical result prepared from the
// source panel. Each data block is read once, without broad workbook dumps.
let formulaCount=0, maxAbsError=0;
for(const sec of sections){
  const got=wb.worksheets.getItem(sec.sheet).getRange(sec.range).values;
  for(let i=0;i<sec.rows.length;i++)for(let j=0;j<sec.colCount;j++){
    const orig=sec.rows[i][j];
    if(orig && typeof orig==='object' && orig.formula){
      const v=got[i]?.[j], e=orig.expected;
      const tol=Math.max(1e-8,Math.abs(e)*1e-11);
      if(typeof v!=='number'||!Number.isFinite(v)||Math.abs(v-e)>tol)throw new Error(`Formula mismatch ${sec.sheet}!${col(j+1)}${sec.row+i}: got ${v}, expected ${e}; ${orig.formula}`);
      formulaCount++;maxAbsError=Math.max(maxAbsError,Math.abs(v-e));
    }
  }
}
// The only freely editable assumptions are those of the educational example.
const ex=wb.worksheets.getItem('1_3_Учебный_пример');
const old=ex.getRange('B7').values[0][0];
ex.getRange('B7').values=[[20]];wb.recalculate();
const changed=ex.getRange('B34').values[0][0];
if(Math.abs(changed-20/Math.sqrt(20))>1e-9)throw new Error('Example input did not recalculate');
ex.getRange('B7').values=[[0]];wb.recalculate();
if(ex.getRange('D34').values[0][0]!==0)throw new Error('Example zero input failed');
ex.getRange('B7').values=[[old]];wb.recalculate();
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:100},summary:'Final formula error scan',maxChars:4000});
await fs.writeFile(path.join(outputDir,'formula_error_scan.ndjson'),errors.ndjson);
const excerpts=[];
for(const [sheet,range] of [['1_3_Учебный_пример','A14:D17'],['2_09_Четыре_структуры','A6:I14'],['3_2_Масштаб_расширения','A6:I10'],['ПБ_Корреляции','A6:D9']]){
  excerpts.push((await wb.inspect({kind:'table',range:`'${sheet}'!${range}`,include:'values,formulas',tableMaxRows:10,tableMaxCols:10,maxChars:2500})).ndjson);
}
await fs.writeFile(path.join(outputDir,'range_inspections.ndjson'),excerpts.join('\n'));
const file=path.join(outputDir,'chip_trade_graph_data.xlsx');
await (await SpreadsheetFile.exportXlsx(wb)).save(file);
console.log(`Exported ${file}; verified ${formulaCount} formulas`);
for(let i=0;i<renders.length;i++){
  const r=renders[i];
  const blob=await wb.render({sheetName:r.sheet,range:r.range,scale:1,format:'png'});
  const fname=`${String(i+1).padStart(2,'0')}_${r.sheet}.png`;
  await fs.writeFile(path.join(previewDir,fname),new Uint8Array(await blob.arrayBuffer()));
  r.file=fname;
  console.log(`Rendered ${r.sheet}`);
}
// Extra views cover the second matrices and the bottom of the longest source
// sheets, without repeatedly rendering the unchanged opening views.
for(const [sheet,range,suffix] of [['ПБ_Корреляции','A19:J28','matrix_korea'],['3_5_Этапы_проекта','A6:F10','stages'],['Месяцы_товары','A190:G198','last_months'],['Оглавление','A60:G76','index_bottom']]){
  const blob=await wb.render({sheetName:sheet,range,scale:1,format:'png'});
  const fname=`extra_${suffix}.png`;await fs.writeFile(path.join(previewDir,fname),new Uint8Array(await blob.arrayBuffer()));
  renders.push({sheet,range,file:fname});
}
await fs.writeFile(path.join(outputDir,'validation.json'),JSON.stringify({figures:spec.catalog.length,sheets:spec.sheets.length,formulaCount,maxAbsError,sourceChecks:spec.checks,inputChangeTest:'passed, original restored',previews:renders},null,2));
console.log(JSON.stringify({file,figures:spec.catalog.length,sheets:spec.sheets.length,formulaCount,maxAbsError}));
