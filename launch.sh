cd ../dora-rs 
export RUSTFLAGS="--cfg tokio_unstable"
cargo build --release --features metrics # opentelemetry_jaeger 
cd ../dora-pylot
cp ../dora-rs/target/release/dora-rs dora-rs
nvidia-docker build --tag dora .
nvidia-docker run -itd --name dora -p 20022:22  dora /bin/bash
nvidia-docker exec -itd dora /home/erdos/workspace/pylot/scripts/run_simulator.sh
nvidia-docker cp ~/.ssh/id_rsa.pub dora:/home/erdos/.ssh/authorized_keys
nvidia-docker exec -i -t dora sudo chown erdos /home/erdos/.ssh/authorized_keys
nvidia-docker exec -i -t dora sudo service ssh start
ssh -p 20022 -X erdos@localhost