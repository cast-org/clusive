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
            ],
            frontend: "frontend/dist",
            frontendcss: "frontend/dist/css",
            frontendjs: "frontend/dist/js"
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
                },
                {
                    // FIXME this seems like an odd place for this, leaving it where it was before
                    // since I'm not sure where else it should go.
                    expand: true,
                    cwd: "node_modules/open-dyslexic",
                    nonull: true,
                    src: "**",
                    dest: "shared/static/shared/js/lib/reader/fonts/open-dyslexic"
                },
                {
                    expand: true,
                    cwd: "node_modules/readium-css/css/dist",
                    nonull: true,
                    src: "**",
                    dest: "shared/static/shared/js/lib/readium-css"
                }]
            },
            frontendcss: {
                expand: true,
                cwd: 'frontend/dist/css',
                nonull: true,
                src: ['**/*'],
                dest: 'shared/static/shared/css'
            },
            frontendjs: {
                files: [
                {
                    expand: true,
                    cwd: 'frontend/js',
                    nonull: true,
                    src: ['**/*'],
                    dest: 'frontend/dist/js'
                },
                {
                    expand: true,
                    cwd: 'frontend/dist/js',
                    nonull: true,
                    src: ['**/*'],
                    dest: 'shared/static/shared/js'
                }]
            },
            frontendfont: {
                expand: true,
                cwd: 'frontend/html/font/',
                nonull: true,
                src: ['**/*'],
                dest: 'shared/static/shared/font/'
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
                    'frontend/dist/css/<%= pkg.name %>-prefs-panel.css': 'frontend/scss/<%= pkg.name %>-prefs-panel.scss',
                    'frontend/dist/css/<%= pkg.name %>-reader-theme-lgdg.css': 'frontend/scss/<%= pkg.name %>-reader-theme-lgdg.scss',
                    'frontend/dist/css/<%= pkg.name %>-reader-theme-bbr.css': 'frontend/scss/<%= pkg.name %>-reader-theme-bbr.scss',
                    'frontend/dist/css/<%= pkg.name %>-reader-theme-gw.css': 'frontend/scss/<%= pkg.name %>-reader-theme-gw.scss',
                    'frontend/dist/css/reader-frame.css': 'frontend/scss/reader-frame.scss'
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
                files: [{
                        expand: true,
                        cwd: 'frontend/dist/css',
                        src: ['*.css', '!*.min.css'],
                        dest: 'frontend/dist/css',
                        ext: '.min.css'
                }]
            },
            frontendfont: {
                files: [{
                        expand: true,
                        cwd: 'frontend/html/font',
                        src: ['**/*.css', '!**/*.min.css'],
                        dest: 'frontend/html/font',
                        ext: '.min.css'
                }]
            }
        },
        eslint: {
            frontend: {
                options: {
                    config: 'frontend/.eslintrc.json',
                    reportUnusedDisableDirectives: 'true',
                },
                src: 'frontend/js/*.js'
            }
        },
        uglify: {
            frontend: {
                options: {
                    mangle: true,
                    output: {
                        comments: /^!|@preserve|@license|@cc_on/i
                    }
                },
                files: [{
                    expand: true,
                    cwd: 'frontend/js',
                    src: ['*.js', '!*.min.js'],
                    dest: 'frontend/dist/js',
                    rename: function (dst, src) {
                        // Keep source js files and make new files as `*.min.js`:
                       return dst + '/' + src.replace('.js', '.min.js');
                    }
                }]
            }
        }
    });

    // Load the plugin(s):
    grunt.loadNpmTasks("@lodder/grunt-postcss");
    grunt.loadNpmTasks("grunt-contrib-copy");
    grunt.loadNpmTasks("grunt-contrib-clean");
    grunt.loadNpmTasks("grunt-contrib-cssmin");
    grunt.loadNpmTasks("grunt-contrib-uglify");
    grunt.loadNpmTasks("grunt-eslint");
    grunt.loadNpmTasks("grunt-sass");
    grunt.loadNpmTasks("grunt-stylelint");
    grunt.loadNpmTasks("grunt-webpack");

    // Custom tasks:
    grunt.registerTask("build", "Build front end JS dependencies and copy over needed static assets from node_modules", ["clean:target", "webpack:dev", "frontend-dist", "copy:lib"]);

    // Frontend build tasks
    grunt.registerTask('frontend-test', ['css-test', 'js-test']);
    grunt.registerTask('frontend-dist', ['css-dist', 'js-dist', 'font-dist']);
    grunt.registerTask('css-test', "Lint front end CSS", ['stylelint:frontend']);
    grunt.registerTask('css-dist', "Build front end CSS and copy to static assets", ['clean:frontendcss', 'sass:frontend', 'postcss:frontend', 'cssmin:frontend', 'copy:frontendcss']);
    grunt.registerTask('js-test', "Lint front end JS", ['eslint:frontend']);
    grunt.registerTask('js-dist', "Build front end JS and copy to static assets", ['clean:frontendjs', 'uglify:frontend', 'copy:frontendjs']);
    grunt.registerTask('font-dist', "Build front end font and copy to static assets", ['cssmin:frontendfont', 'copy:frontendfont']);
}
