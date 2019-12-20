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
            target: "target",
//            frontend: "target/frontend/dist",
            frontendcss: "target/shared/static/shared/css",
            frontendjs: "target/shared/static/shared/js"
        },
        copy: {
            python: {
                files: [
                    {
                        expand: true,
                        cwd: "src",
                        nonull: true,
                        src: ["clusive_project/**", "eventlog/**", "glossary/**", "library/**", "pages/**", "roster/**", "shared/**", "wordnet/**",
                            "manage.py"],
                        dest: "target"
                    }
                ]
            },
            lib: {
                files: [
                {
                    expand: true,
                    cwd: "node_modules/infusion/dist",
                    nonull: true,
                    src: "**",
                    dest: "target/shared/static/shared/js/lib/infusion/dist"
                },
                {
                    expand: true,
                    cwd: "node_modules/infusion/src",
                    nonull: true,
                    src: "**",
                    dest: "target/shared/static/shared/js/lib/infusion/src"
                },
                {
                    expand: true,
                    cwd: "node_modules/figuration/dist",
                    nonull: true,
                    src: "**",
                    dest: "target/shared/static/shared/js/lib/figuration"
                }, {
                    expand: true,
                    cwd: "node_modules/@d-i-t-a/reader/dist",
                    nonull: true,
                    src: "**",
                    dest: "target/shared/static/shared/js/lib/reader"
                },
                {
                    // FIXME this seems like an odd place for this, leaving it where it was before
                    // since I'm not sure where else it should go.
                    expand: true,
                    cwd: "node_modules/open-dyslexic",
                    nonull: true,
                    src: "**",
                    dest: "target/shared/static/shared/js/lib/reader/fonts/open-dyslexic"
                },
                {
                    expand: true,
                    cwd: "node_modules/readium-css/css/dist",
                    nonull: true,
                    src: "**",
                    dest: "target/shared/static/shared/js/lib/readium-css"
                }]
            },
            frontendjs: {
                files: [
                {
                    expand: true,
                    cwd: 'src/frontend/js',
                    nonull: true,
                    src: ['**/*'],
                    dest: 'target/shared/static/shared/js'
                }]
            },
            frontendfont: {
                expand: true,
                cwd: 'src/frontend/html/font/',
                nonull: true,
                src: ['**/*'],
                dest: 'target/shared/static/shared/font/'
            }

        },
        stylelint: {
            frontend: {
                options: {
                    configFile: 'src/frontend/scss/.stylelintrc'
                },
                src: ['src/frontend/scss/**/*.scss']
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
                    'target/shared/static/shared/css/<%= pkg.name %>.css': 'src/frontend/scss/<%= pkg.name %>.scss',
                    'target/shared/static/shared/css/<%= pkg.name %>-prefs-panel.css': 'src/frontend/scss/<%= pkg.name %>-prefs-panel.scss',
                    'target/shared/static/shared/css/<%= pkg.name %>-reader-theme-sepia.css': 'src/frontend/scss/<%= pkg.name %>-reader-theme-sepia.scss',
                    'target/shared/static/shared/css/<%= pkg.name %>-reader-theme-night.css': 'src/frontend/scss/<%= pkg.name %>-reader-theme-night.scss',
                    'target/shared/static/shared/css/reader-frame.css': 'src/frontend/scss/reader-frame.scss'
                }
            }
        },
        postcss: {
            frontend: {
                options: {
                    map: false,
                    processors: [flexbugs, calc, autoprefixer]
                },
                src: ['target/shared/static/shared/css/*.css', '!target/shared/static/shared/css/*.min.css']
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
                        cwd: 'target/shared/static/shared/css',
                        src: ['*.css', '!*.min.css'],
                        dest: 'target/shared/static/shared/css',
                        ext: '.min.css'
                }]
            },
            frontendfont: {
                files: [{
                        expand: true,
                        cwd: 'target/shared/static/shared/font',
                        src: ['**/*.css', '!**/*.min.css'],
                        dest: 'target/shared/static/shared/font',
                        ext: '.min.css'
                }]
            }
        },
        eslint: {
            frontend: {
                options: {
                    config: 'src/frontend/.eslintrc.json',
                    reportUnusedDisableDirectives: 'true',
                },
                src: 'src/frontend/js/*.js'
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
                    cwd: 'target/shared/static/shared/js',
                    src: ['*.js', '!*.min.js'],
                    dest: 'target/shared/static/shared/js',
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
    grunt.registerTask("build", "Build front end JS dependencies and copy over needed static assets from node_modules",
        ["clean:target", "copy:python", "frontend-dist", "webpack:dev", "copy:lib"]);

    // Frontend build tasks
    grunt.registerTask('frontend-test', ['css-test', 'js-test']);
    grunt.registerTask('frontend-dist', ['css-dist', 'js-dist', 'font-dist']);
    grunt.registerTask('css-test', "Lint front end CSS", ['stylelint:frontend']);
    grunt.registerTask('css-dist', "Build front end CSS and copy to static assets", ['clean:frontendcss', 'sass:frontend', 'postcss:frontend', 'cssmin:frontend']);
    grunt.registerTask('js-test', "Lint front end JS", ['eslint:frontend']);
    grunt.registerTask('js-dist', "Build front end JS and copy to static assets", ['copy:frontendjs', 'uglify:frontend']);
    grunt.registerTask('font-dist', "Build front end font and copy to static assets", ['copy:frontendfont', 'cssmin:frontendfont']);
};
