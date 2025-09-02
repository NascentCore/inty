#### Build-logic构建方式配置说明

> `gradle`项目的构建几经迭代，从最原始的`gradle,ext`配置，到后来的`buildSrc`方式，再到现在
`build components`的模式，都是为了解耦构建于项目之间的效能、速率于质量稳定等问题。

目前项目使用的`build-logic`即是构建解耦项目`Project`的一种高效的构建方式，具体详细可参照`gradle`
官方文档，在此处仅介绍一些本工程的相关基础描述。

##### 一、`build-logic`组成

`build-logic`名称也是一个约定通用的文件夹命名，内部可理解为一个独立的`gradle`的构建项目：

- `settings.gradle.kts`也就是项目总配置文件(
  `kotlin语言对应的是kts文件，如果是groovy的则settings.gradle`)
    - 定义了`repositories`和`versionCatalogs`，便于管理`version.toml`文件，用于整个被管理工程项目所有
      `module`的依赖库
    - 可`include`子模块`module`根据需要，决定是否定义，以及定义多少个。
- `build.gradle.kts`即此`build-logic`项目的构建配置文件
    - 顶部`plugins`中使用不同的插件，表示内部用不同语言实现自定义的`gradle plugin`管理项目
        - `kotlin-dsl`、`java-gradle-plugin（？是否正确？）`、`groovy-gradle-plugin（？是否正确？）`等
    - 内部定义`dependencies`内有`classpath`可供自定义`plugin`等引用库及`api`
    - `gradlePlugin`内部`plugins`可`register`注册该`build-logic`内自定义的`plugin(需要实现Plugin<T>)`
        - 注意注册时`id`不可重复已有的插件`id`，且对应实现类的引用地址要`package.className`的全路径的形式。
- 可以创建`module`的形式，将代码写在`module`之内，也可直接定义`src/main/kotlin(或java)`将代码写在该路径下，在内部定义
  `package`更合适一些。

##### 二、使用

- 需要在引入的项目的`settings.gradle.kts`中的`pluginManagement`闭包内`includeBuild("build-logic")`
  然后构建工程
- 在定义配置便捷的可复用函数，以及自定义`plugins`实现类后，定义并注册好`plugins`在上述`build.gradle`中的
  `gradlePlugin`包内。
- 构建`build-logic`模块，使之生成相应插件
- 在对应项目中，各自模块`module`的`build.gradle`中引入需要的自定义`plugin`，就可节省重复配置，精简项目管理
