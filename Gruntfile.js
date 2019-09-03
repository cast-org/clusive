module.exports = function (grunt) {

    var webpackConfig = require("./webpack.config");

    "use strict";

    grunt.initConfig({
        webpack: {
            dev: webpackConfig,
            prod: Object.assign(webpackConfig, {mode: "production"})
        },
        clean: {
            target: "shared/static/shared/js"
        }
    })


    // Load the plugin(s):

    grunt.loadNpmTasks("grunt-contrib-copy");
    grunt.loadNpmTasks("grunt-contrib-clean");
    grunt.loadNpmTasks("grunt-webpack");
    
}