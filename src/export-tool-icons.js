// Export locally installed app icons. No third-party artwork is redistributed.
ObjC.import('AppKit');
ObjC.import('Foundation');

function run(argv) {
  if (argv.length !== 1) throw new Error('Expected an output directory');
  const output = argv[0];
  const fm = $.NSFileManager.defaultManager;
  fm.createDirectoryAtPathWithIntermediateDirectoriesAttributesError(output, true, $(), $());
  const workspace = $.NSWorkspace.sharedWorkspace;
  const tools = [
    { name: 'claude', ids: ['com.anthropic.claudefordesktop'], paths: ['/Applications/Claude.app'], symbol: 'terminal' },
    { name: 'codex', ids: ['com.openai.codex'], paths: ['/Applications/Codex.app', '/Applications/ChatGPT.app'], symbol: 'terminal' },
    { name: 'workbuddy', ids: ['com.workbuddy.workbuddy', 'com.tencent.workbuddy.mac'], paths: ['/Applications/WorkBuddy.app'], symbol: 'person.crop.square' },
  ];
  for (const tool of tools) {
    let appPath = tool.paths.find(path => fm.fileExistsAtPath(path));
    if (!appPath) {
      for (const id of tool.ids) {
        const url = workspace.URLForApplicationWithBundleIdentifier(id);
        if (url && !url.isNil()) { appPath = ObjC.unwrap(url.path); break; }
      }
    }
    const image = appPath ? workspace.iconForFile(appPath)
      : $.NSImage.imageWithSystemSymbolNameAccessibilityDescription(tool.symbol, tool.name);
    const bitmap = $.NSBitmapImageRep.imageRepWithData(image.TIFFRepresentation);
    const png = bitmap.representationUsingTypeProperties($.NSPNGFileType, $({}));
    if (!png.writeToFileAtomically(output + '/' + tool.name + '.png', true)) {
      throw new Error('Could not write icon: ' + tool.name);
    }
  }
}
