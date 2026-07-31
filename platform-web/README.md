**项目改装** | [中文](./README.zh-CN.md)
### 1.项目基础配置和部分目录介绍

- utils/http 使用 vueuse 封装的接口请求，axios 只是引入，未作封装
- store 使用 pinia 做状态管理，线上对数据做了加密处理，开发环境未做处理
- hook 如有经常使用的 hooks，可以自行封装，可以放在目录下与同事一起分享
- unocss 原子化 css，根据个人喜好，可以自行选择是否使用
- 项目样式使用 tailwindcss 规范，如无特殊需求建议减少使用自定义样式，如需使用，请使用原子化 css
- components/Table/index 为项目主要表格组件，ui 无特殊需求，建议使用此组件
- /components/google 谷歌验证码组件，
- /utils/color getTextColor 根据数据大小，显示字体颜色

### 2.常用工具及部分常用函数介绍

- useApiBasic 仅进行接口调用并无特殊数据处理时，可使用此函数，函数进行简单成功，失败返回处理
- utils/options/basicOptions.tsx 静态状态管理文件
- utils/options/useBasicOptions.tsx 异步状态管理文件
- /components/OptionTranslate TextTranslate 状态翻译组件，根据状态码返回对应文字，可设置对应文案颜色

### 3.路由

- 路由通过系统管理-菜单管理进行配置，项目初始时可和后端配合提前预设默认路由，不然页面可能会出现空白
- 不同项目-路由样式可能不同，可以根据现实需求自定义路由组件
- 路由变化时会移除尚未加载成功的后端接口
