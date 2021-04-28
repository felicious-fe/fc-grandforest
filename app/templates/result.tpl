<!doctype html>
<html lang="en">
    <head>
        <meta charset="utf-8">
        <title>Federated GrandForest</title>
        <base href="/">
        <meta charset="utf-8"/>
        <meta http-equiv="X-UA-Compatible" content="IE=edge"/>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://fonts.googleapis.com/css?family=Open+Sans" rel="stylesheet">
        <script src="https://cdn.plot.ly/plotly-latest.min.js" charset="utf-8"></script>
        <link rel="icon" href="assets/fc.ico">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bulma@0.9.1/css/bulma.min.css">
        <script src="https://kit.fontawesome.com/0206581977.js" crossorigin="anonymous"></script>
        <style>
            .center {
                width: 100%;
                text-align: center;
            }
        </style>
    </head>

    <body>
        <div class="main-wrapper">
            <main>
                <section class="hero is-link is-small">
                    <div class="hero-body">
                        <div class="container is-fluid">
                            <section class="section" style="padding: 1rem 1rem;">
                                <h1 class="title">
                                    Federated GrandForest
                                </h1>
                            </section>
                        </div>
                    </div>
                </section>


                <div class="container is-fluid">
                    <div class="card" style="margin-bottom: 15px;">
                        <header class="card-header">
                            <h2 class="card-header-title">Feature Importances</h2>
                        </header>
                        <div class="card-content">
                            <div class="center">
                                TODO
                                {{tables['feature_importance_table']}}
                                {{figures['feature_importance_plot_importances']}}
                                {{figures['feature_importance_plot_network']}}
                            </div>
                        </div>
                    </div>
                </div>

                <div class="container is-fluid">
                    <div class="card" style="margin-bottom: 15px;">
                        <header class="card-header">
                            <h2 class="card-header-title">Endophenotypes</h2>
                        </header>
                        <div class="card-content">
                            <div class="center">
                                TODO
                                {{figures['endophenotypes_plot_heatmap']}}
                                <div display={{survival_visibility}}>
                                	{{figures['endophenotypes_plot_survival']}}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="container is-fluid" display={{prediction_visibility}}>
                    <div class="card" style="margin-bottom: 15px;">
                        <header class="card-header">
                            <h2 class="card-header-title">Prediction</h2>
                        </header>
                        <div class="card-content">
                            <div class="center">
                                TODO
                                {{tables['prediction_results_table']}}
                            </div>
                        </div>
                    </div>
                </div>

            </main>
        </div>

    </body>
</html>