/*:
 * @target MZ
 * @plugindesc 工程测试扩展示例，放在 Debug.js 之后。
 */
(() => {
    if (!Utils.isOptionValid('test')) return;
    if (!window.Debug) throw new Error('Debug_Project requires Debug.js');
    Debug.register('projectInfo', {
        description: '查看当前工程名称',
        parameters: {},
        handler: async () => ({title: $dataSystem.gameTitle})
    });
})();
