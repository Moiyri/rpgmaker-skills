/*:
 * @target MZ
 * @plugindesc Minimal test commands and overlay. Test mode only; backquote toggles HUD, slash opens input.
 * @help Register commands with Debug.register(). Agent and overlay share handlers.
 */
(() => {
    if (!Utils.isOptionValid('test')) return;
    if (window.Debug) throw new Error('Debug already exists');
    const commands = new Map();
    let busy = false;
    const state = () => ({
        scene: SceneManager._scene?.constructor.name,
        mapId: window.$gameMap?.mapId(),
        x: window.$gamePlayer?.x, y: window.$gamePlayer?.y,
        transferring: window.$gamePlayer?.isTransferring(),
        error: document.querySelector('#errorPrinter')?.innerText || ''
    });
    function waitUntil(predicate, timeout = 20000) {
        const start = performance.now();
        return new Promise((resolve, reject) => {
            function check() {
                try {
                    if (state().error) throw new Error(state().error);
                    if (predicate()) return resolve();
                    if (performance.now() - start > timeout) throw new Error('Timeout: ' + JSON.stringify(state()));
                    setTimeout(check, 16);
                } catch (error) { reject(error); }
            }
            check();
        });
    }
    class DebugCore {
        constructor() { this.operations = new Map(); }
        async track(id, name, args) {
            if (this.operations.has(id)) throw new Error('Duplicate operation ID');
            if (!commands.has(name)) throw new Error('Unknown command: ' + name);
            const operation = {id, name, status: 'running'};
            this.operations.set(id, operation);
            // Retain running operations and the latest 100 completed results.
            const completed = [...this.operations.values()].filter(x => x.status !== 'running');
            for (const old of completed.slice(0, Math.max(0, completed.length - 99))) this.operations.delete(old.id);
            try {
                operation.result = await this[name](args);
                operation.status = 'succeeded';
                return operation.result;
            } catch (error) {
                operation.error = String(error?.stack || error);
                operation.status = 'failed';
                throw error;
            }
        }
        operation(id) {
            return this.operations.get(id) || {id, status: 'unknown'};
        }
        commands() { return Array.from(commands.values()); }
        register(name, {description, parameters = {}, handler}) {
            if (!/^[A-Za-z][A-Za-z0-9]*$/.test(name) || name in this) throw new Error('Invalid or duplicate command');
            commands.set(name, {name, description, parameters});
            this[name] = async (args = {}) => {
                if (!args || typeof args !== 'object' || Array.isArray(args)) throw new Error('Expected arguments object');
                for (const key of Object.keys(args)) if (!(key in parameters)) throw new Error('Unknown argument: ' + key);
                for (const [key, spec] of Object.entries(parameters)) {
                    if (spec.required && !(key in args)) throw new Error('Missing argument: ' + key);
                    if (key in args && spec.type === 'integer' && (!Number.isInteger(args[key]) || args[key] < spec.minimum)) throw new Error('Invalid argument: ' + key);
                }
                if (busy) throw new Error('Another operation is running');
                busy = true;
                try { return await handler(args); } finally { busy = false; }
            };
        }
    }
    const api = new DebugCore();
    api.register('state', {description: '返回当前场景、地图和玩家位置', handler: async () => state()});
    api.register('loadGame', {
        description: '读取指定存档，完成引擎读档后处理并等待地图就绪；不等待开场事件结束',
        parameters: {slot: {type: 'integer', minimum: 1, required: true, description: '手动存档编号，从 1 开始'}},
        handler: async ({slot}) => {
            if (!DataManager.savefileInfo(slot)) throw new Error('Save slot unavailable: ' + slot);
            SceneManager.goto(Scene_Load);
            await waitUntil(() => SceneManager._scene instanceof Scene_Load && SceneManager._scene.isStarted() && !SceneManager.isSceneChanging());
            const scene = SceneManager._scene;
            let failure = false;
            const originalFailure = scene.onLoadFailure;
            scene.onLoadFailure = function() { failure = true; return originalFailure.call(this); };
            try {
                scene.executeLoad(slot);
                await waitUntil(() => {
                    if (failure) throw new Error('Engine failed to load slot ' + slot);
                    return scene._loadSuccess && SceneManager._scene !== scene &&
                        SceneManager._scene instanceof Scene_Map && SceneManager._scene.isStarted() &&
                        !SceneManager.isSceneChanging() && !$gamePlayer.isTransferring();
                });
                return {slot, ...state()};
            } finally { scene.onLoadFailure = originalFailure; }
        }
    });
    // Hooks are independent of registered game commands.
    const configPath = typeof process !== 'undefined' ? process.env.RM_EVENT_TEST_CONFIG : null;
    const config = configPath ? JSON.parse(require('fs').readFileSync(configPath, 'utf8')) : null;
    const fields = {
        'game.ready': [], 'runtime.error': ['origin'], 'runtime.warning': ['origin'],
        'event.start': ['mapId','eventId','commonEventId','executionId','parentId'],
        'event.call': ['mapId','eventId','commonEventId','executionId','parentId'],
        'event.command': ['mapId','eventId','commonEventId','executionId','parentId','index','sourceIndex','code','phase'],
        'event.end': ['mapId','eventId','commonEventId','executionId','parentId'],
        'variable.change': ['id','value'], 'switch.change': ['id','value']
    };
    const hooks = new Map(), groups = new Map(), records = [];
    let finish = false, ready = false, executionCounter = 0, parent = null, callingCommon = null;
    const executions = new WeakMap();
    const clone = value => {
        if (value === undefined) return null;
        try { return JSON.parse(JSON.stringify(value)); }
        catch (_) { return String(value); }
    };
    const equal = (a,b) => JSON.stringify(a) === JSON.stringify(b);
    function emit(on, data = {}) {
        const matched = [];
        for (const h of hooks.values()) {
            if (h.active && h.on === on && Object.entries(h.match).every(([k,v]) => equal(data[k],v))) {
                matched.push(h.id);
                if (h.once) h.active = false;
                if (h.action === 'finish') finish = true;
            }
        }
        if (matched.length) records.push({time: Date.now(), signal: on, hooks: matched, ...clone(data)});
        reconcile();
    }
    function install(group) {
        const restores = [];
        const wrap = (object, name, build) => {
            const original = object[name], replacement = build(original);
            object[name] = replacement;
            restores.push(() => { if (object[name] === replacement) object[name] = original; });
        };
        const listen = (name, fn) => {
            window.addEventListener(name, fn);
            restores.push(() => window.removeEventListener(name, fn));
        };
        const error = (origin, value) => emit('runtime.error', {origin,
            message: String(value?.message || value), stack: String(value?.stack || '')});
        if (group === 'ready') {
            wrap(Scene_Map.prototype, 'start', original => function() {
                const result = original.apply(this, arguments);
                if (!ready) { ready = true; emit('game.ready', state()); }
                return result;
            });
        } else if (group === 'error') {
            listen('error', e => error('window.error', e.error || e.message));
            listen('unhandledrejection', e => error('unhandledrejection', e.reason));
            wrap(SceneManager, 'catchException', original => function(e) {
                error('SceneManager.catchException', e); return original.apply(this, arguments);
            });
            wrap(console, 'error', original => function(...args) {
                error('console.error', args.map(x => String(x?.stack || x)).join(' '));
                return original.apply(this,args);
            });
        } else if (group === 'warning') {
            wrap(console, 'warn', original => function(...args) {
                emit('runtime.warning', {origin: 'console.warn', message: args.map(String).join(' ')});
                return original.apply(this,args);
            });
        } else if (group === 'variable' || group === 'switch') {
            const proto = group === 'variable' ? Game_Variables.prototype : Game_Switches.prototype;
            wrap(proto, 'setValue', original => function(id,value) {
                const oldValue = clone(this.value(id));
                const result = original.apply(this,arguments);
                const newValue = clone(this.value(id));
                if (!equal(oldValue,newValue)) emit(group+'.change', {id,oldValue,newValue,value:newValue});
                return result;
            });
        } else if (group === 'event') {
            const info = obj => ({mapId: obj._mapId, eventId: obj._eventId, ...executions.get(obj)});
            wrap(Game_Interpreter.prototype, 'setup', original => function(list,eventId) {
                const result = original.apply(this,arguments);
                executions.set(this, {executionId: ++executionCounter,
                    parentId: parent ? executions.get(parent)?.executionId ?? null : null,
                    commonEventId: callingCommon ?? (config && list === config.commands ? config.source.common_event_id ?? null : null),
                    sourceOffset: config && list === config.commands ? config.range[0] : null});
                emit('event.start', info(this)); return result;
            });
            wrap(Game_Interpreter.prototype, 'setupChild', original => function() {
                const previous = parent; parent = this;
                try { return original.apply(this,arguments); } finally { parent = previous; }
            });
            wrap(Game_Interpreter.prototype, 'command117', original => function(params) {
                const previous = callingCommon;
                callingCommon = params[0];
                if ($dataCommonEvents[params[0]]) emit('event.call', {...info(this),commonEventId:params[0]});
                try { return original.apply(this,arguments); } finally { callingCommon = previous; }
            });
            wrap(Game_Interpreter.prototype, 'executeCommand', original => function() {
                const cmd = this.currentCommand(), index = this._index;
                const data = {...info(this), index,
                    sourceIndex: executions.get(this)?.sourceOffset != null ? executions.get(this).sourceOffset+index : null,
                    code: cmd?.code};
                if (cmd) emit('event.command', {...data,phase:'before'});
                const result = original.apply(this,arguments);
                if (cmd && result) emit('event.command', {...data,phase:'after'});
                return result;
            });
            wrap(Game_Interpreter.prototype, 'terminate', original => function() {
                const running = !!this._list, data = info(this);
                const result = original.apply(this,arguments);
                if (running) emit('event.end',data);
                return result;
            });
        }
        return () => { for (const restore of restores.reverse()) restore(); };
    }
    function groupFor(on) {
        if (on.startsWith('event.')) return 'event';
        return {'game.ready':'ready','runtime.error':'error','runtime.warning':'warning',
                'variable.change':'variable','switch.change':'switch'}[on];
    }
    function reconcile() {
        const needed = new Set([...hooks.values()].filter(h => h.active).map(h => groupFor(h.on)));
        for (const [group,restore] of groups) if (!needed.has(group)) { restore(); groups.delete(group); }
        for (const group of needed) if (!groups.has(group)) groups.set(group,install(group));
    }
    api.hooks = {
        add(h) {
            if (!h || typeof h.id !== 'string' || !h.id.trim() || hooks.has(h.id)) throw new Error('Invalid or duplicate hook ID');
            if (!Object.hasOwn(fields,h.on) || !['record','finish'].includes(h.action) || typeof h.once !== 'boolean') throw new Error('Invalid hook');
            if (!h.match || typeof h.match !== 'object' || Array.isArray(h.match) || Object.keys(h.match).some(k => !fields[h.on].includes(k))) throw new Error('Invalid hook filters');
            hooks.set(h.id,{...clone(h),active:true}); reconcile(); return clone(hooks.get(h.id));
        },
        list() { return clone([...hooks.values()]); },
        remove(id) { const removed=hooks.delete(id); reconcile(); return removed; },
        clear() { hooks.clear(); reconcile(); },
        poll(cursor=0) { return {events:clone(records.slice(cursor)),cursor:records.length,finish}; }
    };
    if (config) {
        for (const h of config.hooks) if (Object.hasOwn(fields,h.on)) api.hooks.add(h);
        // Event test boot and save redirection are separate from hook observation.
        Scene_Boot.prototype.startNormalGame = function() {
            window.$testEvent = config.commands;
            DataManager.setupEventTest();
            SceneManager.goto(Scene_Map);
        };
        StorageManager.fileDirectoryPath = () => config.saveDirectory + '/';
    }

    class DebugControl {
        constructor(tag) { this.element = document.createElement(tag); }
        mount(parent) { parent.appendChild(this.element); return this; }
    }
    class DebugOverlay {
        constructor(core) {
            this.core = core; this.logs = []; this.maxLogs = 50; this.inputActive = false;
            this.root = document.createElement('div'); this.root.id = 'rm-debug-console';
            this.root.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;box-sizing:border-box;pointer-events:none;z-index:1000;font-family:HackNerdFont-Regular,monospace;font-size:14px;color:#fff;background:transparent;padding:8px;display:none;';
            this.hud = document.createElement('div');
            this.hud.style.cssText = 'color:#00ff66;font-size:12px;margin-bottom:6px;white-space:pre;pointer-events:none;height:60px;overflow:hidden;';
            this.logElement = document.createElement('div');
            this.logElement.style.cssText = 'overflow:auto;max-height:calc(100% - 120px);padding-bottom:40px;';
            this.input = new DebugControl('input').element; this.input.type = 'text';
            this.input.placeholder = '输入调试命令...';
            this.input.style.cssText = 'height:28px;box-sizing:content-box;background:rgba(0,0,0,0.5);color:#fff;border:1px solid #555;padding:4px;display:none;position:absolute;bottom:20px;left:8px;width:calc(100% - 34px);pointer-events:auto;font:inherit;';
            this.root.append(this.hud,this.logElement,this.input); document.body.appendChild(this.root);
            this.keydown = e => {
                if (e.code === 'Backquote') {
                    e.preventDefault(); e.stopImmediatePropagation(); this.setVisible(this.root.style.display === 'none'); return;
                }
                if (e.key === '/' && !this.inputActive) {
                    e.preventDefault(); e.stopImmediatePropagation(); this.setVisible(true); this.activateInput(); return;
                }
                if (!this.inputActive) return;
                e.stopImmediatePropagation();
                if (e.key === 'Escape' || e.key === '/') { e.preventDefault(); this.deactivateInput(); }
                else if (e.key === 'Enter' && !e.isComposing) {
                    e.preventDefault(); const text = this.input.value.trim();
                    if (text) { this.addLog('log','> ' + text); this.addLog('warn','命令执行尚未接入'); }
                    this.input.value = '';
                }
            };
            this.keyup = e => { if (this.inputActive) e.stopImmediatePropagation(); };
            window.addEventListener('keydown',this.keydown,true); window.addEventListener('keyup',this.keyup,true);
            for (const type of ['pointerdown','pointerup','mousedown','mouseup','touchstart','touchend','click']) this.input.addEventListener(type,e => e.stopPropagation());
            this.input.addEventListener('focus',()=>{this.inputActive=true;Input.clear();TouchInput.clear();});
            this.input.addEventListener('blur',()=>{this.inputActive=false;Input.clear();TouchInput.clear();});
            this.originals = {}; this.wrappers = {};
            for (const type of ['log','warn','error']) {
                this.originals[type] = console[type];
                this.wrappers[type] = (...args) => {
                    const text = args.map(arg => { try { return typeof arg === 'object' ? JSON.stringify(arg) : String(arg); } catch (_) { return String(arg); } }).join(' ');
                    this.addLog(type,text); this.originals[type].apply(console,args);
                };
                console[type] = this.wrappers[type];
            }
            this.timer = setInterval(()=>{if(this.root.style.display !== 'none')this.updateHud();},200);
        }
        updateHud() {
            const map = window.$gameMap, player = window.$gamePlayer;
            const id = map?.mapId() || 0;
            this.hud.textContent = `Map: ${id} (${window.$dataMapInfos?.[id]?.name || 'Unknown'})\nPos: ${player?.x ?? '-'}, ${player?.y ?? '-'}  Dir: ${player?.direction() ?? '-'}\nScene: ${SceneManager._scene?.constructor.name || 'None'}\nFPS: ${Graphics._fpsMeter?.fps ?? 'N/A'}`;
        }
        addLog(type,message) {
            this.logs.push({type,message}); if(this.logs.length>this.maxLogs)this.logs.shift();
            this.logElement.replaceChildren(...this.logs.map(log=>{
                const row=document.createElement('div'); row.textContent=log.message;
                row.style.whiteSpace='pre-wrap'; row.style.color=log.type==='warn'?'#ffcc00':log.type==='error'?'#ff3333':'#fff';return row;
            }));
            this.logElement.scrollTop=this.logElement.scrollHeight;
        }
        setVisible(visible) {
            this.root.style.display=visible?'block':'none';
            if(visible)this.updateHud();else this.deactivateInput();
        }
        activateInput() { this.input.style.display='block';this.input.focus(); }
        deactivateInput() { this.inputActive=false;this.input.style.display='none';this.input.blur();Input.clear();TouchInput.clear();document.querySelector('canvas')?.focus(); }
        destroy() {
            this.deactivateInput();clearInterval(this.timer);
            window.removeEventListener('keydown',this.keydown,true);window.removeEventListener('keyup',this.keyup,true);
            for(const type of ['log','warn','error'])if(console[type]===this.wrappers[type])console[type]=this.originals[type];
            this.root.remove();
        }
    }
    window.Debug = api;
    api.classes = {DebugCore, DebugOverlay, DebugControl};
    const mount = () => {
        // Place hook wrappers outside the HUD console wrappers so removal restores them.
        for (const group of ['error','warning']) {
            if (groups.has(group)) { groups.get(group)(); groups.delete(group); }
        }
        api.overlay = new DebugOverlay(api);
        reconcile();
    };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, {once:true});
    else mount();
})();
