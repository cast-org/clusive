module.exports = function (grunt) {

    var webpackConfig = require("./webpack.config");
    var autoprefixer = require('autoprefixer');
    var flexbugs = require('postcss-flexbugs-fixes');
    var calc = require('postcss-calc');
    var sass = require('node-sass');

    "use strict";

    grunt.initConfig({
        pkg: grunt.file.readJSON('package.json'),

        webpack: {
            dev: webpackConfig,
            prod: Object.assign(webpackConfig, {mode: "production"})
        },
        clean: {
            target: [
                "shared/static/shared/js/lib",
                "shared/static/shared/css"
            ]
        },
        copy: {
            lib: {
                files: [
                {
                    expand: true,
                    cwd: "node_modules/infusion/dist",
                    nonull: true,
                    src: "**",
                    dest: "shared/static/shared/js/lib/infusion/dist"
                },
                {
                    expand: true,
                    cwd: "node_modules/infusion/src",
                    nonull: true,
                    src: "**",
                    dest: "shared/static/shared/js/lib/infusion/src"
                },
                {
                    expand: true,
                    cwd: "node_modules/figuration/dist",
                    nonull: true,
                    src: "**",
                    dest: "shared/static/shared/js/lib/figuration"
                }, {
                    expand: true,
                    cwd: "node_modules/@dita/reader/dist",
                    nonull: true,
                    src: "**",
                    dest: "shared/static/shared/js/lib/reader"
                }, 
                {
                    expand: true,
                    cwd: "node_modules/@dita/reader/viewer/fonts",
                    nonull: true,
                    src: "**",
                    dest: "shared/static/shared/js/lib/reader/fonts"
                },
                {
                    expand: true,
                    cwd: "node_modules/readium-css/css/dist",
                    nonull: true,
                    src: "**",
                    dest: "shared/static/shared/js/lib/readium-css"
                },
                {
                    expand: true,
                    cwd: "node_modules/popper.js/dist/",
                    nonull: true,
                    src: "**",
                    dest: "shared/static/shared/js/lib/popper.js"
                }]
            }
        },
        sass: {
            options: {
                implementation: sass,
                includePaths: ['scss'],
                precision: 6,
                sourceComments: false,
                sourceMap: false,
                outputStyle: 'expanded'
            },
            core: {
                files: {
                    'shared/static/shared/css/<%= pkg.name %>.css': 'frontend/scss/<%= pkg.name %>.scss',
                    'shared/static/shared/css/<%= pkg.name %>-prefs-panel.css': 'frontend/scss/<%= pkg.name %>-prefs-panel.scss',                    
                    'shared/static/shared/css/<%= pkg.name %>-reader-theme-bw.css': 'frontend/scss/<%= pkg.name %>-reader-theme-bw.scss',                    
                }
            }
        },
        postcss: {
            core: {
                options: {
                    map: false,
                    processors: [flexbugs, calc, autoprefixer]
                },
                src: ['shared/static/shared/css/*.css', '!shared/static/shared/css/*.min.css']
            }
        },
        cssmin: {
            options: {
                report: 'gzip',
                specialComments: '*',
                sourceMap: false,
                advanced: false
            },
            core: {
                files: [
                    {
                        expand: true,
                        cwd: 'shared/static/shared/css',
                        src: ['*.css', '!*.min.css'],
                        dest: 'shared/static/shared/css',
                        ext: '.min.css'
                    }
                ]
            }
        }
    })

    // Load the plugin(s):
    grunt.loadNpmTasks("grunt-contrib-copy");
    grunt.loadNpmTasks("grunt-contrib-clean");
    grunt.loadNpmTasks("grunt-contrib-cssmin");
    grunt.loadNpmTasks("@lodder/grunt-postcss");
    grunt.loadNpmTasks("grunt-sass");
    grunt.loadNpmTasks("grunt-webpack");

    // Custom tasks:
    grunt.registerTask("build", "Build front end JS dependencies and copy over needed static assets from node_modules", ["clean:target", "webpack:dev", "css-dist", "copy:lib"]);

    // CSS build task
    grunt.registerTask('css-dist', "Build front end CSS and copy to static assets", ['sass:core', 'postcss:core', 'cssmin:core']);
}
