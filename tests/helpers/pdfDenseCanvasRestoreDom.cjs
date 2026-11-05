'use strict';
// Explicit DOM/drawing doubles only. Real bundled Canvas owns its initialization,
// collections, event dispatch, selection, transforms, clear/add/remove and links.
const no=()=>{};let document;
function element(tag='canvas'){
 const attrs=new Map(),context=new Proxy({measureText:()=>({width:1})},{get:(target,key)=>key in target?target[key]:no,set:(target,key,value)=>(target[key]=value,true)});
 const e={tagName:tag.toUpperCase(),nodeType:1,width:300,height:150,style:{cssText:'',setProperty:no,removeProperty:no},className:'',classList:{add:no,remove:no,contains:()=>false},
  hasAttribute:key=>attrs.has(key),setAttribute:(key,value)=>attrs.set(key,String(value)),getAttribute:key=>attrs.get(key)??null,removeAttribute:key=>attrs.delete(key),
  getContext:()=>context,getBoundingClientRect:()=>({left:0,top:0,width:840,height:240}),addEventListener:no,removeEventListener:no,
  ownerDocument:document,parentNode:null,parentElement:null,children:[],clientLeft:0,clientTop:0,scrollLeft:0,scrollTop:0,
  append(...nodes){for(const n of nodes)this.appendChild(n);},appendChild(n){n.parentNode=this;n.parentElement=this;this.children.push(n);return n;},
  removeChild(n){const i=this.children.indexOf(n);if(i>=0)this.children.splice(i,1);n.parentNode=null;n.parentElement=null;return n;},
  replaceChild(a,b){const i=this.children.indexOf(b);if(i>=0)this.children[i]=a;a.parentNode=this;a.parentElement=this;b.parentNode=null;b.parentElement=null;return b;},
  contains(n){return this===n||this.children.some(child=>child.contains(n));},focus:no,blur:no};
 context.canvas=e;return e;
}
const window={devicePixelRatio:1,requestAnimationFrame:()=>1,cancelAnimationFrame:no,addEventListener:no,removeEventListener:no,getComputedStyle:()=>({borderLeftWidth:'0',borderTopWidth:'0',paddingLeft:'0',paddingTop:'0',position:'static'})};
document={createElement:element,getElementById:()=>null,addEventListener:no,removeEventListener:no,defaultView:window,documentElement:{clientLeft:0,clientTop:0},body:null};document.body=element('body');
module.exports={element,environment:{document,window,dispose:no}};
