var webpack = require('webpack');
const path = require('path');

module.exports = {
    mode: 'development',
    entry: {
        main: './src/index.js',
        internal: './src/internal.js'
    },
    output: {
        filename: '[name].js',
        path: path.resolve(__dirname, 'target/shared/static/shared/js/lib')
    },
    resolve: {
        alias: {
            infusion: "infusion/dist/infusion-uio-no-jquery.min.js",
            "popper.js": "popper.js/dist/umd/popper.min.js",
            figuration: "figuration/dist/js/figuration.min.js",
            masonry: "masonry-layout/dist/masonry.pkgd.min.js",
            "mark.js": "mark.js/dist/jquery.mark.min.js"
        }
    }
};
