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
        .loader {
            display: inline-block;
            margin: 0 auto;
            padding: 3px;
            border: 16px solid #f3f3f3; /* Light grey */
            border-top: 16px solid #3273dc; /* FeatureCloud Blue */
            border-radius: 50%;
            width: 120px;
            height: 120px;
            animation: spin 2s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

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
                    <div class="card-content">
                        <div class="center">
                            <div class="loader"></div>
                            </br></br>
                            {{status}}
                            </br></br>
                            <button class="button is-link" onClick="window.location.href=window.location.href">Refresh Page</button>
                        </div>
                    </div>
                </div>
            </div>
        </main>
    </div>
    
</body>
