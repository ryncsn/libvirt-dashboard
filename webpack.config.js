var webpack = require('webpack');
module.exports = {
  context: __dirname + "/app/static",
  entry: {
    // Vendors
    vendor: ['jquery', 'bootstrap-webpack', 'font-awesome-webpack', './pack/datatables.js', './pack/style.js', ],
    // The script that will load before any page content loaded.
    head: './pack/pace.js',
    // Initial Script for all page.
    init: ['./pack/style.js', './lib/sharedParameters.js'],
    // Page specified entry.
    column_table: './column_table.js',
    resolve_auto: './resolve_auto.js',
    resolve_manual: './resolve_manual.js',
    testrun_dashboard: './testrun_dashboard.js',
    testrun_overview: './testrun_overview.js',
    testrun_diff: './testrun_diff.js',
    job_trigger: './job_trigger.js',
  },
  output: {
    path: __dirname + '/app/static/dist/',
    publicPath: '/app/static/dist/',
    filename: "[name].js"
  },
  module: {
    preLoaders: [
      {
        test: /\.js$/, // include .js files
        exclude: /node_modules/, // exclude any and all files in the node_modules folder
        loader: "jshint"
      }
    ],
    loaders: [
      // BS FA Fonts
      { test: /\.(woff|woff2)(\?v=\d+\.\d+\.\d+)?$/, loader: 'url?limit=10000&mimetype=application/font-woff' },
      { test: /\.ttf(\?v=\d+\.\d+\.\d+)?$/, loader: 'url?limit=10000&mimetype=application/octet-stream' },
      { test: /\.eot(\?v=\d+\.\d+\.\d+)?$/, loader: 'file' },
      { test: /\.svg(\?v=\d+\.\d+\.\d+)?$/, loader: 'url?limit=10000&mimetype=image/svg+xml' },
      // Style
      { test: /\.css$/, loader: "style!css" },
      // HACK, pace-progress have a broken AMD definetion, disable "define" variable can disable AMD, force use CommonJS.
      { test: require.resolve("pace-progress"), loader: "imports?define=>false" },
      { test: /\.vue$/, loader: 'vue' },
      // babel
      {
        test: /\.js$/,
        exclude: /(node_modules|bower_components)/,
        loader: 'babel', // 'babel-loader' is also a valid name to reference
        query: {
          presets: ['es2015']
        }
      }
    ]
  },
  vue: {
    loaders: {
      js: 'babel?presets[]=es2015'
    }
  },
  jshint: {
    esversion: 6,
    camelcase: false,
    emitErrors: false,
    failOnHint: false,
  },
  plugins: [
    // ProvidePlugin make sure if "$" or "jQuery" is used in a module,
    // jquery is auto loaded as a dependency.
    // CommonChuckPlugin("vendor", ...) bundle all modules in "vendor" entry defined above
    // in a common bundle, when any of them are required, it will be imported from that bundle,
    // and HTML templates/pages should alway load this common bundle before any other
    // module may need it.
    new webpack.ProvidePlugin({
      $: "jquery",
      jQuery: "jquery",
      "window.jQuery": "jquery"
    }),
    new webpack.optimize.CommonsChunkPlugin("vendor", "vendor.bundle.js"),
  ],
  resolve: {
    alias: {
      'vue$': 'vue/dist/vue.js'
    }
  }
};
