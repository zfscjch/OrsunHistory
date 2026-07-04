const { minify } = require('html-minifier-terser');
const fs = require('fs').promises;
const path = require('path');
const glob = require('glob');

// 配置压缩选项，你可以根据需求调整这些参数
const minifyOptions = {
    collapseWhitespace: true,
    removeComments: true,
    minifyJS: true,
    minifyCSS: true,
    // 更多选项请参考官方文档 [citation:5][citation:9]
};

async function build() {
    // 1. 定义源文件夹和目标文件夹
    const srcDir = './src';    // 你的 HTML 源文件所在文件夹
    const distDir = './templates';  // 压缩后文件的输出文件夹

    // 2. 使用 glob 递归匹配 src 目录下所有 .html 文件
    const htmlFiles = glob.sync(`${srcDir}/**/*.html`, { ignore: '**/node_modules/**' });

    // 3. 确保目标文件夹存在
    await fs.mkdir(distDir, { recursive: true });

    // 4. 遍历并压缩每个文件
    for (const filePath of htmlFiles) {
        try {
            // 读取文件内容
            const content = await fs.readFile(filePath, 'utf8');
            // 执行压缩
            const minifiedContent = await minify(content, minifyOptions);

            // 构建输出路径：保持和源文件相同的相对路径，但根目录替换为 templates
            const relativePath = path.relative(srcDir, filePath);
            const outputPath = path.join(distDir, relativePath);

            // 确保输出文件所在的子目录存在
            await fs.mkdir(path.dirname(outputPath), { recursive: true });
            // 写入压缩后的文件
            await fs.writeFile(outputPath, minifiedContent);

            console.log(`✅ 压缩成功: ${filePath} -> ${outputPath}`);
        } catch (error) {
            console.error(`❌ 压缩失败: ${filePath}`, error.message);
        }
    }
    console.log('🎉 全部 HTML 文件压缩完成！');
}

build();