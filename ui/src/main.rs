#[macro_use]
extern crate rocket;

mod db;
mod models;
mod routes;

use rocket::fs::{FileServer, relative};
use rocket_dyn_templates::Template;

#[launch]
fn rocket() -> _ {
    rocket::build()
        .attach(Template::fairing())
        .mount("/", routes::index_routes())
        .mount("/api", routes::api_routes())
        .mount("/static", FileServer::from(relative!("static")))
}
