const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const template = fs.readFileSync('templates/tickets/_ai_assistant.html', 'utf8');
const render = template.slice(template.indexOf('    function render(messages)'), template.indexOf('    function schedule(delay)'));
function element() {
  return {children: [], style: {}, appendChild(child) { this.children.push(child); }, addEventListener() {}};
}
const latest = {hidden: true};
const conversation = {scrollTop: 300, scrollHeight: 900,
  replaceChildren(fragment) { this.children = fragment.children; this.scrollHeight = 1300; }};
const context = vm.createContext({
  lastMessages: '', revealLatest: true, followResponse: true,
  conversation, find: () => latest,
  document: {createElement: element, createDocumentFragment: element},
});
vm.runInContext(render, context);
const initial = {id:1,role:'assistant', content:'Initial analysis',status:'completed'};
const question = {id:2,role:'user', content:'What next?',status:'completed'};
const pending = {id:3,role:'assistant', content:'',status:'pending'};
context.messages = [initial, question, pending];
vm.runInContext('render(messages)', context);
assert.equal(conversation.scrollTop, 0, 'Submission reveals latest exchange');
assert.equal(conversation.children[0].children[1].textContent, 'What next?');
assert.equal(conversation.children[1].children[1].textContent, 'Waiting for analysis…');
context.messages = [initial, question, {...pending, content:'Try this next.',status:'completed'}];
vm.runInContext('render(messages)', context);
assert.equal(conversation.children[1].children[1].textContent, 'Try this next.');
assert.equal(conversation.scrollTop, 0, 'Completed response stays visible');
context.followResponse = false;
conversation.scrollTop = 300;
context.messages = [...context.messages,{id:4,role:'user',content:'Another technician question',status:'completed'}];
vm.runInContext('render(messages)', context);
assert.equal(latest.hidden, false, 'Reading older content exposes latest-message button');
console.log('AI question/response ordering, pending/completed updates, and scroll tests passed');
