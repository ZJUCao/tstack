## 给 Troy 的摘要

### 对你有什么变化

`recipe-menu init` 会新建一个数据文件夹，里面有示例的设置、目录、库存和一个菜谱。文件夹里已经有东西时，它拒绝并且什么都不改。中途出错时，它删掉自己建的东西。

### 需要你决定的事

1. **以空格或点结尾的文件夹名（Windows）** 方案 1：所有命令都用 Windows 实际使用的文件夹；方案 2：除 `init` 外都报告文件夹不存在；方案 3：不改。推荐：方案 1，因为每个命令看到的是同一个文件夹。
2. **“已有文件”的含义** 方案 1：任何条目都算；方案 2：只有文件算。推荐：方案 1，因为 `init` 不会把它的文件和你的混在一起。
3. **数据文件夹上面缺少的文件夹** 方案 1：`init` 创建它们，失败后再删掉；方案 2：`init` 拒绝。推荐：方案 1，因为一步就能建好深层的新文件夹。

回复「全按推荐」即可全部采用推荐，或写出编号和你选的方案。

### 风险

没有发现风险。

## Summary for Troy

### What changes for you

`recipe-menu init` creates a new data folder with the example settings, catalog, pantry, and one recipe. When the folder already holds something, it refuses and changes nothing. When it fails part way, it removes what it created.

### What you decide

1. **Folder names that end with a space or a dot, on Windows.** Option 1: every command uses the folder that Windows uses. Option 2: every command but `init` reports the folder as missing. Option 3: no change. Recommended: option 1, because every command then sees the same folder.
2. **What "holds files" means.** Option 1: every entry counts. Option 2: only files count. Recommended: option 1, because `init` never mixes its files with yours.
3. **Missing folders above the data folder.** Option 1: `init` creates them, and removes them after a failure. Option 2: `init` refuses. Recommended: option 1, because you can name a new folder deep down in one step.

Reply "all as recommended" (全按推荐) to take every recommendation, or give the number and the option you want.

### Risks

None found.
