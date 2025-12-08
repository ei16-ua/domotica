package main

import (
	"database/sql"
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	_ "github.com/mattn/go-sqlite3"
)

const (
	Port     = ":8080"
	FilesDir = "./material_files"
	DBPath   = "./materials.db"
)

var db *sql.DB

type Material struct {
	ID           int64  `json:"id"`
	SubjectID    string `json:"subject_id"`
	Title        string `json:"title"`
	LogicalType  string `json:"logical_type"`
	FilePath     string `json:"file_path"`
	OriginalName string `json:"original_name"`
	MimeType     string `json:"mime_type"`
	Description  string `json:"description"`
	CreatedAt    string `json:"created_at"`
}

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", DBPath)
	if err != nil {
		log.Fatal(err)
	}

	createTableSQL := `CREATE TABLE IF NOT EXISTS material (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		subject_id TEXT NOT NULL,
		title TEXT NOT NULL,
		logical_type TEXT NOT NULL,
		file_path TEXT NOT NULL,
		original_name TEXT NOT NULL,
		mime_type TEXT,
		description TEXT,
		created_at TEXT NOT NULL
	);`

	_, err = db.Exec(createTableSQL)
	if err != nil {
		log.Fatal(err)
	}
}

func listMaterial() ([]Material, error) {
	rows, err := db.Query("SELECT id, subject_id, title, logical_type, file_path, original_name, mime_type, description, created_at FROM material ORDER BY created_at DESC")
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var materials []Material
	for rows.Next() {
		var m Material
		var mimeType, description sql.NullString
		err = rows.Scan(&m.ID, &m.SubjectID, &m.Title, &m.LogicalType, &m.FilePath, &m.OriginalName, &mimeType, &description, &m.CreatedAt)
		if err != nil {
			return nil, err
		}
		if mimeType.Valid {
			m.MimeType = mimeType.String
		}
		if description.Valid {
			m.Description = description.String
		}
		materials = append(materials, m)
	}
	return materials, nil
}

func addMaterial(m Material) (int64, error) {
	stmt, err := db.Prepare("INSERT INTO material (subject_id, title, logical_type, file_path, original_name, mime_type, description, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)")
	if err != nil {
		return 0, err
	}
	defer stmt.Close()

	res, err := stmt.Exec(m.SubjectID, m.Title, m.LogicalType, m.FilePath, m.OriginalName, m.MimeType, m.Description, m.CreatedAt)
	if err != nil {
		return 0, err
	}
	return res.LastInsertId()
}

func getPathsForSubject(subjectID string) ([]string, error) {
	rows, err := db.Query("SELECT file_path FROM material WHERE subject_id = ?", subjectID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var paths []string
	for rows.Next() {
		var p string
		if err := rows.Scan(&p); err == nil {
			paths = append(paths, p)
		}
	}
	return paths, nil
}

func main() {
	initDB()
	defer db.Close()

	if err := os.MkdirAll(FilesDir, 0755); err != nil {
		log.Fatal(err)
	}

	r := gin.Default()

	// Config CORS
	r.Use(cors.New(cors.Config{
		AllowOrigins:     []string{"*"},
		AllowMethods:     []string{"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"},
		AllowHeaders:     []string{"Origin", "Content-Type", "Accept"},
		ExposeHeaders:    []string{"Content-Length"},
		AllowCredentials: true,
	}))

	r.Static("/material_files", FilesDir) // Servir archivos estáticos si es necesario

	api := r.Group("/api")
	{
		api.GET("/material", func(c *gin.Context) {
			materials, err := listMaterial()
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}
			// Si es nil, devolver array vacío en vez de null
			if materials == nil {
				materials = []Material{}
			}
			c.JSON(http.StatusOK, materials)
		})

		api.GET("/material/paths/:subject_id", func(c *gin.Context) {
			subjectID := c.Param("subject_id")
			paths, err := getPathsForSubject(subjectID)
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}
			if paths == nil {
				paths = []string{}
			}
			c.JSON(http.StatusOK, gin.H{"subject_id": subjectID, "paths": paths})
		})

		api.POST("/material/upload", func(c *gin.Context) {
			subjectID := c.PostForm("subject_id")
			title := c.PostForm("title")
			logicalType := c.PostForm("logical_type")
			description := c.PostForm("description")

			file, err := c.FormFile("file")
			if err != nil {
				c.JSON(http.StatusBadRequest, gin.H{"error": "No file is received"})
				return
			}

			// Crear directorio para la asignatura
			subjectDir := filepath.Join(FilesDir, strings.TrimSpace(subjectID))
			if err := os.MkdirAll(subjectDir, 0755); err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create subject directory"})
				return
			}

			ts := time.Now().Unix()
			safeName := strings.ReplaceAll(file.Filename, " ", "_")
			destPath := filepath.Join(subjectDir, fmt.Sprintf("%d_%s", ts, safeName))

			// Guardar archivo
			if err := c.SaveUploadedFile(file, destPath); err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to save file"})
				return
			}

			// Guardar en BBDD
			newID, err := addMaterial(Material{
				SubjectID:    strings.TrimSpace(subjectID),
				Title:        strings.TrimSpace(title),
				LogicalType:  strings.TrimSpace(logicalType),
				FilePath:     destPath,
				OriginalName: file.Filename,
				MimeType:     file.Header.Get("Content-Type"),
				Description:  strings.TrimSpace(description),
				CreatedAt:    time.Now().Format(time.RFC3339),
			})

			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to save record to DB"})
				return
			}

			c.JSON(http.StatusOK, gin.H{
				"status":      "ok",
				"id":          newID,
				"stored_path": destPath,
			})
		})
	}

	fmt.Printf("Server running on http://127.0.0.1%s\n", Port)
	r.Run(Port)
}
