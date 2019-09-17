module.exports = function (grunt) {

    var webpackConfig = require("./webpack.config");

    "use strict";

    grunt.initConfig({
        webpack: {
            dev: webpackConfig,
            prod: Object.assign(webpackConfig, {mode: "production"})
        },
        clean: {
            target: "shared/static/shared/js/lib"
        },
        copy: {
            lib: {
                files: [
                {
                    expand: true,
                    cwd: "node_modules/infusion/dist",
                    src: "**",
                    dest: "shared/static/shared/js/lib/infusion/dist"
                },
                {
                    expand: true,
                    cwd: "node_modules/infusion/src",
                    src: "**",
                    dest: "shared/static/shared/js/lib/infusion/src"
                },
                {
                    expand: true,
                    cwd: "node_modules/figuration/dist",
                    src: "**",
                    dest: "shared/static/shared/js/lib/figuration"
                }, {
                    expand: true,
                    cwd: "node_modules/@dita/reader/dist",
                    src: "**",
                    dest: "shared/static/shared/js/lib/reader"
                }]
            }
        }
    })


    // Load the plugin(s):

    grunt.loadNpmTasks("grunt-contrib-copy");
    grunt.loadNpmTasks("grunt-contrib-clean");
    grunt.loadNpmTasks("grunt-webpack");

    // Custom tasks:
    grunt.registerTask("build", "Build front end JS dependencies and copy over needed static assets from node_modules", ["clean:target", "webpack:dev", "copy:lib"])
    
}