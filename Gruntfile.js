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
                "shared/static/shared/css/*.css"
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
                    cwd: "node_modules/@d-i-t-a/reader/dist",
                    nonull: true,
                    src: "**",
                    dest: "shared/static/shared/js/lib/reader"
                }, {
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
            },
            frontend: {
                expand: true,
                cwd: 'frontend/dist/css/',
                nonull: true,
                src: ['**/*'],
                dest: 'shared/static/shared/css/'
            }

        },
        stylelint: {
            frontend: {
                options: {
                    configFile: 'frontend/scss/.stylelintrc'
                },
                src: ['frontend/scss/**/*.scss']
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
            frontend: {
                files: {
                    'frontend/dist/css/<%= pkg.name %>.css': 'frontend/scss/<%= pkg.name %>.scss',
                    'frontend/dist/css/<%= pkg.name %>-prefs-panel.css': 'frontend/scss/<%= pkg.name %>-prefs-panel.scss'
                }
            }
        },
        postcss: {
            frontend: {
                options: {
                    map: false,
                    processors: [flexbugs, calc, autoprefixer]
                },
                src: ['frontend/dist/css/*.css', '!frontend/dist/css/*.min.css']
            }
        },
        cssmin: {
            options: {
                report: 'gzip',
                specialComments: '*',
                sourceMap: false,
                advanced: false
            },
            frontend: {
                files: [
                    {
                        expand: true,
                        cwd: 'frontend/dist/css',
                        src: ['*.css', '!*.min.css'],
                        dest: 'frontend/dist/css',
                        ext: '.min.css'
                    }
                ]
            }
        }
    });

    // Load the plugin(s):
    grunt.loadNpmTasks("@lodder/grunt-postcss");
    grunt.loadNpmTasks("grunt-contrib-copy");
    grunt.loadNpmTasks("grunt-contrib-clean");
    grunt.loadNpmTasks("grunt-contrib-cssmin");
    grunt.loadNpmTasks("grunt-sass");
    grunt.loadNpmTasks("grunt-stylelint");
    grunt.loadNpmTasks("grunt-webpack");

    // Custom tasks:
    grunt.registerTask("build", "Build front end JS dependencies and copy over needed static assets from node_modules", ["clean:target", "webpack:dev", "css-dist", "copy:lib"]);

    // CSS build task
    grunt.registerTask('css-test', "Lint front end CSS", ['stylelint:frontend']);
    grunt.registerTask('css-dist', "Build front end CSS and copy to static assets", ['sass:frontend', 'postcss:frontend', 'cssmin:frontend', 'copy:frontend']);
}
