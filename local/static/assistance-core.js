(function(root){
'use strict';
const normalize=s=>s.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim();
const commands={copiar:['C','LGUI'],colar:['V','LGUI'],recortar:['X','LGUI'],desfazer:['Z','LGUI'],salvar:['S','LGUI'],'selecionar tudo':['A','LGUI'],print:['N4','LGUI','LSHFT'],captura:['N4','LGUI','LSHFT'],'limpar bluetooth':['BT_CLR'],usb:['OUT_USB'],bluetooth:['OUT_BLE'],enter:['ENTER'],espaco:['SPACE'],backspace:['BSPC'],esc:['ESC'],tab:['TAB'],esquerda:['LEFT'],direita:['RIGHT'],cima:['UP'],baixo:['DOWN']};
const synonyms={LGUI:['LCMD','LEFT_GUI'],LSHFT:['LSHIFT','LEFT_SHIFT'],SPACE:['SPC'],ENTER:['RET','RETURN'],BSPC:['BACKSPACE'],LEFT:['LEFT_ARROW'],RIGHT:['RIGHT_ARROW'],UP:['UP_ARROW'],DOWN:['DOWN_ARROW'],LBKT:['LBRACKET'],RBKT:['RBRACKET']};
const symbols={'@':['N2',true],'!':['N1',true],'#':['N3',true],'$':['N4',true],'%':['N5',true],'^':['N6',true],'&':['N7',true],'*':['N8',true],'(':['N9',true],')':['N0',true],'-':['MINUS',false],'_':['MINUS',true],'=':['EQUAL',false],'+':['EQUAL',true],'[':['LBKT',false],']':['RBKT',false],'{':['LBKT',true],'}':['RBKT',true],';':['SEMI',false],':':['SEMI',true],"'":['SQT',false],'"':['SQT',true],'/':['SLASH',false],'?':['SLASH',true],'\\':['BSLH',false],'|':['BSLH',true],'`':['GRAVE',false],'~':['GRAVE',true],',':['COMMA',false],'<':['COMMA',true],'.':['DOT',false],'>':['DOT',true]};
function codeMatches(binding,code){const values=[code,...(synonyms[code]||[])];return values.some(c=>binding==='&kp '+c||binding==='&bt '+c||binding==='&out '+c);}
function effective(layers,layer,position,active=[0,layer]){for(const i of [...new Set(active)].sort((a,b)=>b-a)){const b=layers[i]?.bindings[position];if(b&&b!=='&trans')return b;}return '&none';}
function paths(layers){const result=new Map([[0,{positions:[],active:[0]}]]),queue=[0];while(queue.length){const from=queue.shift(),state=result.get(from);for(let p=0;p<38;p++){const b=effective(layers,from,p,state.active),m=b.match(/^&mo (\d+)$/);if(!m)continue;const to=+m[1];if(to>from&&to<layers.length&&!result.has(to)&&!state.positions.includes(p)){result.set(to,{positions:[...state.positions,p],active:[...state.active,to]});queue.push(to);}}}return result;}
function resolve(layers,query,inputMap='us'){
 if(!layers.length||!query.trim())return [];
 const q=normalize(query),symbol=query==='arroba'?'@':query;
 let codes=commands[q],shift=false;
 if(!codes&&/^[a-zA-Z0-9]$/.test(query)){codes=[/\d/.test(query)?'N'+query:query.toUpperCase()];shift=/^[A-Z]$/.test(query);}
 if(!codes&&symbols[symbol]){if(inputMap!=='us')return [];codes=[symbols[symbol][0]];shift=symbols[symbol][1];}
 if(!codes&&/^f\d{1,2}$/.test(q))codes=[q.toUpperCase()];
 const reachable=paths(layers),answers=[];
 if(codes){
  if(shift)codes=[...codes,'LSHFT'];
  for(const [layer,state] of reachable){
   const path=state.positions,active=state.active;
   const main=layers[layer].bindings.findIndex((_,p)=>codeMatches(effective(layers,layer,p,active),codes[0]));if(main<0)continue;
   const mods=codes.slice(1).map(code=>layers[layer].bindings.findIndex((_,p)=>codeMatches(effective(layers,layer,p,active),code)));
   if(mods.some(p=>p<0))continue;
   const positions=[...new Set([...path,...mods,main])];
   if(path.includes(main)||mods.some(p=>path.includes(p)))continue;
   answers.push({layer,positions,main,label:query,binding:effective(layers,layer,main,active),active,hold:[...new Set([...path,...mods])]});
  }
 } else {
  for(const [layer,state] of reachable)layers[layer].bindings.forEach((_,p)=>{const binding=effective(layers,layer,p,state.active);if(!['&none','&trans'].includes(binding)&&normalize(binding).includes(q))answers.push({layer,positions:[...state.positions,p],main:p,hold:state.positions,active:state.active,label:binding,binding,advanced:true});});
 }
 return answers.sort((a,b)=>a.positions.length-b.positions.length).slice(0,8);
}
function observe(stats,target,previous,value){
 if(value.length<=previous.length)return;
 let common=0;while(common<previous.length&&common<value.length&&previous[common]===value[common])common++;
 // Count only an insertion immediately after a correct prefix; corrections do not count twice.
 if(previous.slice(0,common)!==target.slice(0,common))return;
 for(let i=common;i<value.length&&i<target.length;i++){
  const expected=target[i];if(!/[a-z0-9 ]/.test(expected))continue;
  const item=stats[expected]||(stats[expected]={hits:0,misses:0});
  if(value[i]===expected)item.hits++;else{item.misses++;break;}
 }
}
function sequence(stats){
 const chars='abcdefghijklmnopqrstuvwxyz'.split('').sort((a,b)=>((stats[b]?.misses||0)*3-(stats[b]?.hits||0)*0.15)-((stats[a]?.misses||0)*3-(stats[a]?.hits||0)*0.15));
 const weak=chars.slice(0,6);return [weak.slice(0,3).join(''),weak.slice(3).join(''),weak.slice().reverse().join(''),'casa','teclado'].join(' ');
}
function diagnostics(state){
 const l=state.telemetry?.sides?.left||{},r=state.telemetry?.sides?.right||{},result=[];
 if(!l.fresh)result.push('Sem dados recentes da esquerda. Conecte a metade esquerda por USB ou reconecte a telemetria Bluetooth.');
 if(l.fresh&&!l.split)result.push('As metades não estão comunicando. Confira se a direita está ligada e carregada.');
 if(l.fresh)result.push(l.endpoint===1?'Saída selecionada: Bluetooth. Isso não comprova que um aplicativo recebeu texto.':'Saída selecionada: USB. Para escrever pelo cabo, use a metade esquerda.');
 if(!r.fresh)result.push('Sem bateria recente da direita. Uma leitura ausente não significa bateria vazia.');
 result.push('Confira a escrita no campo de teste do macOS no topo do editor. A saída ZMK mostra comandos gerados, não o texto recebido.');
 return result;
}
const api={resolve,effective,observe,sequence,diagnostics};if(typeof module!=='undefined')module.exports=api;else root.TotemAssist=api;
})(typeof window==='undefined'?globalThis:window);
