pipeline {
    agent any

    environment {
        PYTHON_BIN = "/usr/bin/python3.11"
        VENV_DIR   = "pyats-venv"
    }

    stages {

        /* =========================
         * TASK 1: CLONE REPOSITORY
         * ========================= */
        stage('Task 1 - Clone repository') {
            steps {
                checkout scm
            }
        }

        /* =========================
         * TASK 2: PYTHON ENV SETUP
         * ========================= */
        stage('Task 2.1 - Verify Python 3.11') {
            steps {
                sh '''
                set -e
                echo "Using Python:"
                $PYTHON_BIN --version
                '''
            }
        }

        stage('Task 2.2 - Create virtualenv') {
            steps {
                sh '''
                set -e
                if [ ! -d "$VENV_DIR" ]; then
                    $PYTHON_BIN -m venv $VENV_DIR
                else
                    echo "Virtualenv already exists, reusing it"
                fi
                '''
            }
        }

        stage('Task 2.3 - Install Python dependencies') {
            steps {
                sh '''
                set -e
                . $VENV_DIR/bin/activate
                pip install --upgrade pip
                pip install -r requirements-pyats-24.3-python311.txt
                '''
            }
        }

        stage('Task 2.4 - Verify pyATS environment') {
            steps {
                sh '''
                set -e
                . $VENV_DIR/bin/activate

                echo "Python version:"
                python --version

                echo "Verifying pyATS stack:"
                python -c "import pyats; print('pyATS version:', pyats.__version__)"
                python -c "import unicon; print('Unicon OK')"
                python -c "import genie; print('Genie OK')"
                '''
            }
        }
    }

    post {
        success {
            echo "✅ Task 1 and Task 2 completed successfully"
        }
        failure {
            echo "❌ Pipeline failed — check stage logs"
        }
    }
}
